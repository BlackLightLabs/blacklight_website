"""
Admin Routes for User and Role Management

This module provides admin-only endpoints for:
- Managing users (list, view, update role, activate/deactivate)
- Managing roles (list, create, update, delete)
- Managing permissions (list, assign/remove from roles)

All routes require superuser or specific admin permissions.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.blacklight.common.audit import set_user_context
from src.blacklight.common.database import get_db
from src.blacklight.features.auth.dependencies import get_permission_service, get_user_repository, get_role_repository, get_permission_repository
from src.blacklight.features.auth.models import User
from src.blacklight.features.auth.repositories import (
    UserRepository,
    RoleRepository,
    PermissionRepository,
)
from src.blacklight.features.auth.routes import current_superuser
from src.blacklight.features.auth.schemas import (
    AssignRoleRequest,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    RoleWithPermissions,
    UpdateUserRoleRequest,
    UserListItem,
    UserWithRole,
)
from src.blacklight.features.auth.services import PermissionService

# Create admin router
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# User Management Endpoints
# ============================================================================


@admin_router.get("/users", response_model=list[UserListItem])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None),
    role_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with optional filtering

    **Requires**: Superuser or users:read permission

    **Query Parameters**:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - search: Search by email or full name
    - role_id: Filter by role ID
    - is_active: Filter by active status
    """
    from sqlalchemy import select, or_

    from src.blacklight.features.auth.models import User, Role

    # Build query
    query = select(User).options(selectinload(User.role))

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(User.email.ilike(search_pattern), User.full_name.ilike(search_pattern))
        )

    if role_id is not None:
        query = query.where(User.role_id == role_id)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Convert to response schema with role name
    user_list = []
    for user in users:
        user_data = UserListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_id=user.role_id,
            role_name=user.role.name if user.role else None,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
        user_list.append(user_data)

    return user_list


@admin_router.get("/users/{user_id}", response_model=UserWithRole)
async def get_user_details(
    user_id: int,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific user

    **Requires**: Superuser or users:read permission
    """
    from sqlalchemy import select

    from src.blacklight.features.auth.models import User

    # Get user with role loaded
    query = select(User).where(User.id == user_id).options(selectinload(User.role))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@admin_router.patch("/users/{user_id}/role", response_model=UserWithRole)
async def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user's role

    **Requires**: Superuser or users:manage_roles permission
    """
    # Set user context for audit logging
    set_user_context(current_user)

    # Get the role to verify it exists
    role = await role_repo.get_by_id(request.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Assign the role to the user
    updated_user = await user_repo.assign_role(user_id, role.id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Manual audit log for role update (not covered by service decorator)
    from src.blacklight.common.audit import log_audit_event
    await log_audit_event(
        db=db,
        event_type="user_management",
        event_action="user_role_updated",
        user_id=current_user.id,
        details={"target_user_id": user_id, "role_id": role.id, "role_name": role.name}
    )

    # Return user with role eagerly loaded
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    result = await user_repo.db.execute(stmt)
    user_with_role = result.scalar_one_or_none()

    return user_with_role


@admin_router.patch("/users/{user_id}/activate", response_model=UserWithRole)
async def activate_user(
    user_id: int,
    current_user: User = Depends(current_superuser),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Activate a user account

    **Requires**: Superuser or users:update permission
    """
    user = await user_repo.activate_user(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@admin_router.patch("/users/{user_id}/deactivate", response_model=UserWithRole)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(current_superuser),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Deactivate a user account

    **Requires**: Superuser or users:update permission
    """
    user = await user_repo.deactivate_user(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


# ============================================================================
# Role Management Endpoints
# ============================================================================


@admin_router.get("/roles", response_model=list[RoleWithPermissions])
async def list_roles(
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
):
    """
    List all roles with their permissions

    **Requires**: Superuser or roles:read permission
    """
    from sqlalchemy import select

    from src.blacklight.features.auth.models import Role

    query = select(Role).options(selectinload(Role.permissions))
    result = await role_repo.db.execute(query)
    roles = result.scalars().all()

    return roles


@admin_router.get("/roles/{role_id}", response_model=RoleWithPermissions)
async def get_role_details(
    role_id: int,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
):
    """
    Get detailed information about a specific role

    **Requires**: Superuser or roles:read permission
    """
    role = await role_repo.get_with_permissions(role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return role


@admin_router.post("/roles", response_model=RoleWithPermissions, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(current_superuser),
    permission_service: PermissionService = Depends(get_permission_service),
    permission_repo: PermissionRepository = Depends(get_permission_repository),
    role_repo: RoleRepository = Depends(get_role_repository),
):
    """
    Create a new role with permissions

    **Requires**: Superuser or roles:create permission
    """
    # Convert permission IDs to permission names if provided
    permission_names = []
    if role_data.permission_ids:
        for perm_id in role_data.permission_ids:
            perm = await permission_repo.get_by_id(perm_id)
            if perm:
                permission_names.append(perm.name)

    # Create role
    role = await permission_service.create_role(
        name=role_data.name, description=role_data.description, permission_names=permission_names
    )

    # Reload with permissions
    role_with_perms = await role_repo.get_with_permissions(role.id)

    return role_with_perms


@admin_router.patch("/roles/{role_id}", response_model=RoleWithPermissions)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a role

    **Requires**: Superuser or roles:update permission
    """
    role = await role_repo.get_by_id(role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Set user context for audit logging
    set_user_context(current_user)

    # Update basic fields
    if role_data.name is not None:
        role.name = role_data.name
    if role_data.description is not None:
        role.description = role_data.description

    # Update permissions if provided
    if role_data.permission_ids is not None:
        await role_repo.set_permissions(role_id, role_data.permission_ids)

    await role_repo.db.commit()

    # Manual audit log
    from src.blacklight.common.audit import log_audit_event
    await log_audit_event(
        db=db,
        event_type="role_management",
        event_action="role_updated",
        user_id=current_user.id,
        details={"role_id": role_id, "role_name": role.name}
    )

    # Reload with permissions
    updated_role = await role_repo.get_with_permissions(role_id)

    return updated_role


@admin_router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a role

    **Requires**: Superuser or roles:delete permission

    **Note**: Cannot delete a role that is assigned to users
    """
    # Set user context for audit logging
    set_user_context(current_user)

    # Check if role exists
    role = await role_repo.get_by_id(role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Check if role is assigned to any users
    users_with_role = await user_repo.get_users_by_role(role_id)

    if users_with_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role that is assigned to {len(users_with_role)} user(s)",
        )

    # Store role name for audit log before deletion
    role_name = role.name

    # Delete role
    await role_repo.db.delete(role)
    await role_repo.db.commit()

    # Manual audit log
    from src.blacklight.common.audit import log_audit_event
    await log_audit_event(
        db=db,
        event_type="role_management",
        event_action="role_deleted",
        user_id=current_user.id,
        details={"role_id": role_id, "role_name": role_name}
    )


# ============================================================================
# Permission Management Endpoints
# ============================================================================


@admin_router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    resource: str | None = Query(None),
    current_user: User = Depends(current_superuser),
    permission_repo: PermissionRepository = Depends(get_permission_repository),
):
    """
    List all permissions

    **Requires**: Superuser or roles:read permission

    **Query Parameters**:
    - resource: Filter by resource name (e.g., 'agents', 'users', 'roles')
    """
    from sqlalchemy import select

    from src.blacklight.features.auth.models import Permission

    query = select(Permission)

    if resource:
        query = query.where(Permission.resource == resource)

    query = query.order_by(Permission.resource, Permission.action)

    result = await permission_repo.db.execute(query)
    permissions = result.scalars().all()

    return permissions


@admin_router.post("/roles/{role_id}/permissions/{permission_id}", response_model=RoleWithPermissions)
async def add_permission_to_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
):
    """
    Add a permission to a role

    **Requires**: Superuser or roles:update permission
    """
    role = await role_repo.add_permission(role_id, permission_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role or permission not found"
        )

    # Reload with permissions
    updated_role = await role_repo.get_with_permissions(role_id)

    return updated_role


@admin_router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=RoleWithPermissions)
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(current_superuser),
    role_repo: RoleRepository = Depends(get_role_repository),
):
    """
    Remove a permission from a role

    **Requires**: Superuser or roles:update permission
    """
    role = await role_repo.remove_permission(role_id, permission_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role or permission not found"
        )

    # Reload with permissions
    updated_role = await role_repo.get_with_permissions(role_id)

    return updated_role
