"""
Permission checking dependencies for RBAC

Provides decorators and dependencies for checking user permissions.
"""

from fastapi import Depends, HTTPException, status

from src.blacklight.features.auth.dependencies import get_permission_service
from src.blacklight.features.auth.models import User
from src.blacklight.features.auth.routes import current_active_user
from src.blacklight.features.auth.services import PermissionService


class PermissionChecker:
    """
    Dependency class for checking user permissions

    Usage:
        @app.get("/agents", dependencies=[Depends(PermissionChecker(["agents:read"]))])
        async def get_agents():
            ...
    """

    def __init__(self, required_permissions: list[str]):
        """
        Initialize permission checker

        Args:
            required_permissions: List of required permission names
        """
        self.required_permissions = required_permissions

    async def __call__(
        self,
        user: User = Depends(current_active_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ):
        """
        Check if user has all required permissions

        Args:
            user: Current authenticated user
            permission_service: Permission service instance

        Raises:
            HTTPException: If user doesn't have required permissions
        """
        for permission in self.required_permissions:
            if not await permission_service.has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}",
                )


class RequirePermission:
    """
    Dependency for requiring a single permission

    Usage:
        @app.post("/agents")
        async def create_agent(
            user: User = Depends(RequirePermission("agents:create"))
        ):
            ...
    """

    def __init__(self, permission: str):
        """
        Initialize permission requirement

        Args:
            permission: Required permission name (e.g., "agents:create")
        """
        self.permission = permission

    async def __call__(
        self,
        user: User = Depends(current_active_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> User:
        """
        Check if user has the required permission

        Args:
            user: Current authenticated user
            permission_service: Permission service instance

        Returns:
            User instance if authorized

        Raises:
            HTTPException: If user doesn't have required permission
        """
        if not await permission_service.has_permission(user, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.permission}",
            )
        return user


class RequireRole:
    """
    Dependency for requiring a specific role

    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            user: User = Depends(RequireRole("admin"))
        ):
            ...
    """

    def __init__(self, role_name: str):
        """
        Initialize role requirement

        Args:
            role_name: Required role name (e.g., "admin")
        """
        self.role_name = role_name

    async def __call__(self, user: User = Depends(current_active_user)) -> User:
        """
        Check if user has the required role

        Args:
            user: Current authenticated user

        Returns:
            User instance if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        # Superusers bypass role check
        if user.is_superuser:
            return user

        if not user.role or user.role.name != self.role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Required role: {self.role_name}"
            )
        return user


# Helper functions for common permission checks


async def require_superuser(user: User = Depends(current_active_user)) -> User:
    """
    Require user to be a superuser

    Args:
        user: Current authenticated user

    Returns:
        User instance if superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required"
        )
    return user


def check_resource_permission(resource: str, action: str):
    """
    Create a permission checker for a specific resource and action

    Args:
        resource: Resource name (e.g., "agents")
        action: Action name (e.g., "create")

    Returns:
        Permission checker dependency

    Usage:
        @app.post("/agents")
        async def create_agent(
            user: User = Depends(check_resource_permission("agents", "create"))
        ):
            ...
    """
    permission_name = f"{resource}:{action}"
    return RequirePermission(permission_name)
