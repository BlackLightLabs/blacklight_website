"""
Authentication and Authorization Repositories

This module contains all repository classes for authentication and authorization:
- UserRepository: User account management and lookup operations
- UserSettingsRepository: User preferences including theme and custom prompts
- RoleRepository: Role management and permission assignment
- PermissionRepository: Permission CRUD and lookup operations
- AuditLogRepository: Security event logging and querying
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.blacklight.common.base_repository import BaseRepository
from src.blacklight.features.auth.models import (
    AuditLog,
    Permission,
    Role,
    User,
    UserSettings,
)


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations

    Extends BaseRepository with user-specific queries like email lookup,
    role filtering, and authentication-related operations.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address

        Args:
            email: User's email address

        Returns:
            User instance if found, None otherwise
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id: int) -> User | None:  # type: ignore[override]  # noqa: A002
        """
        Get user by ID (overrides base to use int instead of str)

        Args:
            id: User's ID

        Returns:
            User instance if found, None otherwise
        """
        stmt = select(User).where(User.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users_by_role(self, role_id: int) -> list[User]:
        """
        Get all users with a specific role

        Args:
            role_id: Role ID to filter by

        Returns:
            List of users with the specified role
        """
        stmt = select(User).where(User.role_id == role_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all active users

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        stmt = select(User).where(User.is_active).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_superusers(self) -> list[User]:
        """
        Get all superusers

        Returns:
            List of superuser accounts
        """
        stmt = select(User).where(User.is_superuser)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_users(self, query: str, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Search users by email or full name

        Args:
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users matching the search query
        """
        search_pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(or_(User.email.ilike(search_pattern), User.full_name.ilike(search_pattern)))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_last_login(self, user_id: int) -> User | None:
        """
        Update user's last login timestamp

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID

        Returns:
            Updated user instance
        """
        from datetime import datetime

        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(user)
        return user

    async def activate_user(self, user_id: int) -> User | None:
        """
        Activate a user account

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID

        Returns:
            Updated user instance
        """
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = True
            await self.db.flush()
            await self.db.refresh(user)
        return user

    async def deactivate_user(self, user_id: int) -> User | None:
        """
        Deactivate a user account

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID

        Returns:
            Updated user instance
        """
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False
            await self.db.flush()
            await self.db.refresh(user)
        return user

    async def assign_role(self, user_id: int, role_id: int) -> User | None:
        """
        Assign a role to a user

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID
            role_id: Role ID to assign

        Returns:
            Updated user instance
        """
        user = await self.get_by_id(user_id)
        if user:
            user.role_id = role_id
            await self.db.flush()
            await self.db.refresh(user)
        return user


class UserSettingsRepository(BaseRepository[UserSettings]):
    """
    Repository for UserSettings model operations

    Provides settings management including theme preferences and custom prompts.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(UserSettings, db)

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """
        Get user settings by user ID

        Args:
            user_id: User's ID

        Returns:
            UserSettings instance if found, None otherwise
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_default_settings(self, user_id: int) -> UserSettings:
        """
        Create default settings for a new user

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID

        Returns:
            Newly created UserSettings instance
        """
        settings = UserSettings(
            user_id=user_id, theme="system", custom_prompts=None, preferences=None
        )
        self.db.add(settings)
        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    async def update_theme(self, user_id: int, theme: str) -> UserSettings | None:
        """
        Update user's theme preference

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID
            theme: Theme name ('light', 'dark', or 'system')

        Returns:
            Updated UserSettings instance
        """
        settings = await self.get_by_user_id(user_id)
        if settings:
            settings.theme = theme
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def update_custom_prompts(
        self, user_id: int, custom_prompts: dict[str, Any]
    ) -> UserSettings | None:
        """
        Update user's custom prompts

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID
            custom_prompts: Dictionary of custom prompts

        Returns:
            Updated UserSettings instance
        """
        settings = await self.get_by_user_id(user_id)
        if settings:
            settings.custom_prompts = custom_prompts
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def update_preferences(
        self, user_id: int, preferences: dict[str, Any]
    ) -> UserSettings | None:
        """
        Update user's general preferences

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID
            preferences: Dictionary of preferences

        Returns:
            Updated UserSettings instance
        """
        settings = await self.get_by_user_id(user_id)
        if settings:
            settings.preferences = preferences
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def update_settings(
        self,
        user_id: int,
        theme: str | None = None,
        custom_prompts: dict[str, Any] | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> UserSettings | None:
        """
        Update multiple user settings fields at once

        Note: Does not commit. Caller must commit the transaction.

        Args:
            user_id: User's ID
            theme: Optional theme name
            custom_prompts: Optional custom prompts dictionary
            preferences: Optional preferences dictionary

        Returns:
            Updated UserSettings instance
        """
        settings = await self.get_by_user_id(user_id)
        if settings:
            if theme is not None:
                settings.theme = theme
            if custom_prompts is not None:
                settings.custom_prompts = custom_prompts
            if preferences is not None:
                settings.preferences = preferences
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def get_or_create(self, user_id: int) -> UserSettings:
        """
        Get existing settings or create default settings for a user

        Args:
            user_id: User's ID

        Returns:
            UserSettings instance (existing or newly created)
        """
        settings = await self.get_by_user_id(user_id)
        if not settings:
            settings = await self.create_default_settings(user_id)
        return settings


class RoleRepository(BaseRepository[Role]):
    """
    Repository for Role model operations

    Provides role management including permission assignment and role hierarchy.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Role | None:
        """
        Get role by name

        Args:
            name: Role name (e.g., 'admin', 'user')

        Returns:
            Role instance if found, None otherwise
        """
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id: int) -> Role | None:  # type: ignore[override]  # noqa: A002
        """
        Get role by ID (overrides base to use int instead of str)

        Args:
            id: Role ID

        Returns:
            Role instance if found, None otherwise
        """
        stmt = select(Role).where(Role.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: int) -> Role | None:
        """
        Get role by ID with permissions eagerly loaded

        Args:
            role_id: Role ID

        Returns:
            Role instance with permissions loaded, None if not found
        """
        stmt = select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_permission(self, role_id: int, permission_id: int) -> Role | None:
        """
        Add a permission to a role

        Note: Does not commit. Caller must commit the transaction.

        Args:
            role_id: Role ID
            permission_id: Permission ID to add

        Returns:
            Updated role instance
        """
        # Use get_with_permissions to eagerly load the relationship
        role = await self.get_with_permissions(role_id)
        if role:
            stmt = select(Permission).where(Permission.id == permission_id)
            result = await self.db.execute(stmt)
            permission = result.scalar_one_or_none()
            if permission and permission not in role.permissions:
                role.permissions.append(permission)
                await self.db.flush()
                await self.db.refresh(role, ["permissions"])
        return role

    async def remove_permission(self, role_id: int, permission_id: int) -> Role | None:
        """
        Remove a permission from a role

        Note: Does not commit. Caller must commit the transaction.

        Args:
            role_id: Role ID
            permission_id: Permission ID to remove

        Returns:
            Updated role instance
        """
        # Use get_with_permissions to eagerly load the relationship
        role = await self.get_with_permissions(role_id)
        if role:
            stmt = select(Permission).where(Permission.id == permission_id)
            result = await self.db.execute(stmt)
            permission = result.scalar_one_or_none()
            if permission and permission in role.permissions:
                role.permissions.remove(permission)
                await self.db.flush()
                await self.db.refresh(role, ["permissions"])
        return role

    async def get_role_permissions(self, role_id: int) -> list[Permission]:
        """
        Get all permissions for a role

        Args:
            role_id: Role ID

        Returns:
            List of permissions
        """
        role = await self.get_by_id(role_id)
        return role.permissions if role else []

    async def set_permissions(self, role_id: int, permission_ids: list[int]) -> Role | None:
        """
        Set all permissions for a role (replaces existing)

        Note: Does not commit. Caller must commit the transaction.

        Args:
            role_id: Role ID
            permission_ids: List of permission IDs to assign

        Returns:
            Updated role instance
        """
        # Use get_with_permissions to eagerly load the relationship
        role = await self.get_with_permissions(role_id)
        if role:
            stmt = select(Permission).where(Permission.id.in_(permission_ids))
            result = await self.db.execute(stmt)
            permissions = list(result.scalars().all())
            role.permissions = permissions
            await self.db.flush()
            await self.db.refresh(role, ["permissions"])
        return role


class PermissionRepository(BaseRepository[Permission]):
    """
    Repository for Permission model operations

    Provides permission management and lookup operations.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)

    async def get_by_name(self, name: str) -> Permission | None:
        """
        Get permission by name

        Args:
            name: Permission name (e.g., 'agents:create')

        Returns:
            Permission instance if found, None otherwise
        """
        stmt = select(Permission).filter(Permission.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id: int) -> Permission | None:  # type: ignore[override]  # noqa: A002
        """
        Get permission by ID (overrides base to use int instead of str)

        Args:
            id: Permission ID

        Returns:
            Permission instance if found, None otherwise
        """
        stmt = select(Permission).filter(Permission.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_resource(self, resource: str) -> list[Permission]:
        """
        Get all permissions for a specific resource

        Args:
            resource: Resource name (e.g., 'agents', 'users')

        Returns:
            List of permissions for the resource
        """
        stmt = select(Permission).filter(Permission.resource == resource)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_action(self, action: str) -> list[Permission]:
        """
        Get all permissions with a specific action

        Args:
            action: Action name (e.g., 'create', 'read', 'update', 'delete')

        Returns:
            List of permissions with the action
        """
        stmt = select(Permission).filter(Permission.action == action)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_resource_and_action(self, resource: str, action: str) -> Permission | None:
        """
        Get permission by resource and action

        Args:
            resource: Resource name
            action: Action name

        Returns:
            Permission instance if found, None otherwise
        """
        stmt = select(Permission).filter(
            Permission.resource == resource, Permission.action == action
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_permission(
        self, resource: str, action: str, description: str | None = None
    ) -> Permission:
        """
        Create a new permission

        Note: Does not commit. Caller must commit the transaction.

        Args:
            resource: Resource name
            action: Action name
            description: Optional description

        Returns:
            Created permission instance
        """
        name = f"{resource}:{action}"
        permission = Permission(
            name=name, resource=resource, action=action, description=description
        )
        self.db.add(permission)
        await self.db.flush()
        await self.db.refresh(permission)
        return permission


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Repository for AuditLog model operations

    Provides audit logging for security-relevant events like login attempts,
    permission denials, and role changes.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def get_by_id(self, id: int) -> AuditLog | None:  # type: ignore[override]  # noqa: A002
        """
        Get audit log by ID (overrides base to use int instead of str)

        Args:
            id: Audit log ID

        Returns:
            AuditLog instance if found, None otherwise
        """
        stmt = select(AuditLog).filter(AuditLog.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def log_event(
        self,
        event_type: str,
        event_action: str,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Log a security event

        Note: Does not commit. Caller must commit the transaction.

        Args:
            event_type: Type of event (e.g., 'login', 'permission_denied')
            event_action: Specific action (e.g., 'login_success', 'agents:create_denied')
            user_id: Optional user ID (nullable for failed login attempts)
            ip_address: Optional IP address
            user_agent: Optional user agent string
            details: Optional additional event context as JSON

        Returns:
            Created audit log instance
        """
        log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_action=event_action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_user_logs(self, user_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        """
        Get audit logs for a specific user

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit logs for the user
        """
        stmt = (
            select(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_logs_by_type(
        self, event_type: str, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        """
        Get audit logs by event type

        Args:
            event_type: Event type to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit logs matching the event type
        """
        stmt = (
            select(AuditLog)
            .filter(AuditLog.event_type == event_type)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_logs(
        self, hours: int = 24, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        """
        Get recent audit logs within specified hours

        Args:
            hours: Number of hours to look back
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of recent audit logs
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(AuditLog)
            .filter(AuditLog.created_at >= cutoff_time)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_login_attempts(self, ip_address: str | None = None, hours: int = 1) -> int:
        """
        Count failed login attempts from an IP address

        Args:
            ip_address: IP address to check
            hours: Number of hours to look back

        Returns:
            Count of failed login attempts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(func.count(AuditLog.id)).filter(
            AuditLog.event_type == "login",
            AuditLog.event_action == "login_failed",
            AuditLog.created_at >= cutoff_time,
        )

        if ip_address:
            stmt = stmt.filter(AuditLog.ip_address == ip_address)

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_permission_denials(self, user_id: int, hours: int = 24) -> list[AuditLog]:
        """
        Get permission denial events for a user

        Args:
            user_id: User ID
            hours: Number of hours to look back

        Returns:
            List of permission denial audit logs
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.event_type == "permission",
                AuditLog.created_at >= cutoff_time,
            )
            .order_by(desc(AuditLog.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
