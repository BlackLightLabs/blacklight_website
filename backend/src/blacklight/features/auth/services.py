"""
Authentication and Permission Services

This module contains two main service classes:
1. AuthService: Provides authentication operations with audit logging
2. PermissionService: Provides RBAC (Role-Based Access Control) functionality

Also includes UserManager which integrates FastAPI-Users with repository pattern.
"""

import structlog
from fastapi import Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.audit import audit_log, log_audit_event
from src.blacklight.common.settings import settings
from src.blacklight.features.auth.models import AuditLog, Permission, Role, User
from src.blacklight.features.auth.repositories import (
    AuditLogRepository,
    PermissionRepository,
    RoleRepository,
    UserRepository,
)

# Get logger for auth feature
logger = structlog.get_logger("blacklight.auth")


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """
    Custom User Manager with audit logging

    Extends FastAPI-Users BaseUserManager to add audit logging for
    authentication events.
    """

    reset_password_token_secret = settings.jwt_secret
    verification_token_secret = settings.jwt_secret

    def __init__(self, user_db: SQLAlchemyUserDatabase, db: AsyncSession):
        super().__init__(user_db)
        self.db = db
        self.audit_repo = AuditLogRepository(db)
        self.user_repo = UserRepository(db)
        self.permission_service = PermissionService(db)

    async def on_after_register(self, user: User, request: Request | None = None):
        """Called after successful user registration."""
        logger.info("user_registered", user_id=user.id, email=user.email)

        # Assign default "user" role to new users
        await self.permission_service.assign_role(user.id, "user")

        # Log registration event using new audit utility
        await log_audit_event(
            db=self.db,
            event_type="registration",
            event_action="user_registered",
            user_id=user.id,
            details={"email": user.email},
            request=request,
        )

    async def on_after_login(self, user: User, request: Request | None = None, response=None):
        """Called after successful login."""
        logger.info("user_logged_in", user_id=user.id, email=user.email)

        # Update last login timestamp
        await self.user_repo.update_last_login(user.id)

        # Log successful login using new audit utility
        await log_audit_event(
            db=self.db,
            event_type="login",
            event_action="login_success",
            user_id=user.id,
            details={"email": user.email},
            request=request,
        )

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        """Called after user requests email verification."""
        logger.info("verification_requested", user_id=user.id, email=user.email)

        # Log verification request using new audit utility
        await log_audit_event(
            db=self.db,
            event_type="verification",
            event_action="verification_requested",
            user_id=user.id,
            request=request,
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        """Called after user requests password reset."""
        logger.info("password_reset_requested", user_id=user.id, email=user.email)

        # Log password reset request using new audit utility
        await log_audit_event(
            db=self.db,
            event_type="password_reset",
            event_action="reset_requested",
            user_id=user.id,
            request=request,
        )


class AuthService:
    """
    Authentication Service

    Provides high-level authentication operations using FastAPI-Users
    integrated with our repository pattern.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    async def log_failed_login(
        self,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        reason: str = "invalid_credentials",
    ):
        """
        Log a failed login attempt

        Args:
            email: Email address attempted
            ip_address: IP address of the attempt
            user_agent: User agent string
            reason: Reason for failure
        """
        # Use the utility function for consistency
        await log_audit_event(
            db=self.db,
            event_type="login",
            event_action="login_failed",
            user_id=None,  # No user ID for failed attempts
            details={"email": email, "reason": reason},
        )

    async def check_rate_limit(
        self, ip_address: str, hours: int = 1, max_attempts: int = 5
    ) -> bool:
        """
        Check if an IP address has exceeded the rate limit for failed logins

        Args:
            ip_address: IP address to check
            hours: Time window in hours
            max_attempts: Maximum allowed failed attempts

        Returns:
            True if within limit, False if exceeded
        """
        failed_attempts = await self.audit_repo.get_failed_login_attempts(ip_address, hours)
        return failed_attempts < max_attempts

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Get user by email

        Args:
            email: User's email address

        Returns:
            User instance if found, None otherwise
        """
        return await self.user_repo.get_by_email(email)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Get user by ID

        Args:
            user_id: User's ID

        Returns:
            User instance if found, None otherwise
        """
        return await self.user_repo.get_by_id(user_id)

    @audit_log("user_management", "user_activated", user_id_param="user_id")
    async def activate_user(self, user_id: int) -> User | None:
        """
        Activate a user account

        Args:
            user_id: User's ID

        Returns:
            Updated user instance
        """
        user = await self.user_repo.activate_user(user_id)
        return user

    @audit_log("user_management", "user_deactivated", user_id_param="user_id")
    async def deactivate_user(self, user_id: int) -> User | None:
        """
        Deactivate a user account

        Args:
            user_id: User's ID

        Returns:
            Updated user instance
        """
        user = await self.user_repo.deactivate_user(user_id)
        return user


class PermissionService:
    """
    Permission Service for RBAC

    Provides methods for checking permissions, managing roles, and
    auditing permission-related events.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)
        self.audit_repo = AuditLogRepository(db)

    async def has_permission(self, user: User, permission_name: str) -> bool:
        """
        Check if a user has a specific permission

        Args:
            user: User instance
            permission_name: Permission name (e.g., 'agents:create')

        Returns:
            True if user has permission, False otherwise
        """
        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Check if user has a role (use role_id column, not relationship)
        if not user.role_id:
            return False

        # Get all permissions for the user's role
        user_permissions = await self.get_user_permissions(user)
        return permission_name in user_permissions

    async def get_user_permissions(self, user: User) -> set[str]:
        """
        Get all permission names for a user

        Args:
            user: User instance

        Returns:
            Set of permission names
        """
        # Superusers have all permissions
        if user.is_superuser:
            all_permissions = await self.permission_repo.get_all()
            return {p.name for p in all_permissions}

        # Get permissions from user's role (load role from DB to avoid lazy loading)
        if not user.role_id:
            return set()

        # Load role with permissions
        role = await self.role_repo.get_with_permissions(user.role_id)
        if not role:
            return set()

        return {p.name for p in role.permissions}

    async def check_permission(
        self, user: User, resource: str, action: str, log_denial: bool = True
    ) -> bool:
        """
        Check if user has permission for a resource and action

        Args:
            user: User instance
            resource: Resource name (e.g., 'agents', 'users')
            action: Action name (e.g., 'create', 'read', 'update', 'delete')
            log_denial: Whether to log permission denials

        Returns:
            True if user has permission, False otherwise
        """
        permission_name = f"{resource}:{action}"
        has_perm = await self.has_permission(user, permission_name)

        # Log permission denial using new audit utility
        if not has_perm and log_denial:
            # Get role name if user has a role (avoid lazy loading)
            role_name = None
            if user.role_id:
                role = await self.role_repo.get_by_id(user.role_id)
                role_name = role.name if role else None

            await log_audit_event(
                db=self.db,
                event_type="permission",
                event_action=f"{permission_name}_denied",
                user_id=user.id,
                details={
                    "resource": resource,
                    "action": action,
                    "email": user.email,
                    "role": role_name,
                },
            )

        return has_perm

    @audit_log("role_management", "role_assigned", user_id_param="user_id", include_args=True)
    async def assign_role(self, user_id: int, role_name: str) -> User | None:
        """
        Assign a role to a user

        Args:
            user_id: User's ID
            role_name: Role name to assign

        Returns:
            Updated user instance
        """
        role = await self.role_repo.get_by_name(role_name)
        if not role:
            return None

        user = await self.user_repo.assign_role(user_id, role.id)
        return user

    @audit_log("role_management", "role_created", include_args=True)
    async def create_role(
        self,
        name: str,
        description: str | None = None,
        permission_names: list[str] | None = None,
    ) -> Role:
        """
        Create a new role with permissions

        Args:
            name: Role name
            description: Optional role description
            permission_names: Optional list of permission names to assign

        Returns:
            Created role instance
        """
        from datetime import datetime

        # Create role
        role = Role(
            name=name,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        # Assign permissions if provided
        if permission_names:
            permissions = []
            for perm_name in permission_names:
                perm = await self.permission_repo.get_by_name(perm_name)
                if perm:
                    permissions.append(perm.id)

            if permissions:
                await self.role_repo.set_permissions(role.id, permissions)

        return role

    @audit_log("permission_management", "permission_created", include_args=True)
    async def create_permission(
        self, resource: str, action: str, description: str | None = None
    ) -> Permission:
        """
        Create a new permission

        Args:
            resource: Resource name
            action: Action name
            description: Optional description

        Returns:
            Created permission instance
        """
        permission = await self.permission_repo.create_permission(resource, action, description)
        return permission

    async def get_role_by_name(self, name: str) -> Role | None:
        """
        Get role by name

        Args:
            name: Role name

        Returns:
            Role instance if found, None otherwise
        """
        return await self.role_repo.get_by_name(name)

    @audit_log("role_management", "permission_added_to_role", include_args=True)
    async def add_permission_to_role(self, role_name: str, permission_name: str) -> Role | None:
        """
        Add a permission to a role

        Args:
            role_name: Role name
            permission_name: Permission name

        Returns:
            Updated role instance
        """
        role = await self.role_repo.get_by_name(role_name)
        permission = await self.permission_repo.get_by_name(permission_name)

        if not role or not permission:
            return None

        role = await self.role_repo.add_permission(role.id, permission.id)
        return role

    async def initialize_default_roles_and_permissions(self):
        """
        Initialize default roles and permissions for the system

        This should be called during application startup or via a migration script.
        """
        # Create default permissions
        permissions_to_create = [
            # Agent permissions
            ("agents", "create", "Create new agents"),
            ("agents", "read", "Read/view agents"),
            ("agents", "update", "Update agents"),
            ("agents", "delete", "Delete agents"),
            ("agents", "execute", "Execute agents"),
            # User management permissions
            ("users", "create", "Create new users"),
            ("users", "read", "Read/view users"),
            ("users", "update", "Update users"),
            ("users", "delete", "Delete users"),
            ("users", "manage_roles", "Manage user roles"),
            # Role management permissions
            ("roles", "create", "Create new roles"),
            ("roles", "read", "Read/view roles"),
            ("roles", "update", "Update roles"),
            ("roles", "delete", "Delete roles"),
        ]

        for resource, action, description in permissions_to_create:
            # Check if permission already exists
            existing = await self.permission_repo.get_by_resource_and_action(resource, action)
            if not existing:
                await self.create_permission(resource, action, description)

        # Create default roles
        default_roles = {
            "superadmin": [
                # Superadmin has all permissions (but is also checked via is_superuser flag)
                "agents:create",
                "agents:read",
                "agents:update",
                "agents:delete",
                "agents:execute",
                "users:create",
                "users:read",
                "users:update",
                "users:delete",
                "users:manage_roles",
                "roles:create",
                "roles:read",
                "roles:update",
                "roles:delete",
            ],
            "admin": [
                "agents:create",
                "agents:read",
                "agents:update",
                "agents:delete",
                "agents:execute",
                "users:read",
                "users:update",
            ],
            "user": [
                "agents:create",
                "agents:read",
                "agents:update",
                "agents:execute",
            ],
            "guest": [
                "agents:read",
            ],
        }

        for role_name, perm_names in default_roles.items():
            # Check if role already exists
            existing_role = await self.role_repo.get_by_name(role_name)
            if not existing_role:
                await self.create_role(role_name, f"Default {role_name} role", perm_names)
