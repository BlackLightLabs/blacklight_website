"""
Auth feature dependencies for FastAPI dependency injection

Provides user database, user manager, and service dependencies for authentication routes.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.database import get_db
from src.blacklight.features.auth.models import OAuthAccount, User
from src.blacklight.features.auth.repositories import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
    UserSettingsRepository,
)
from src.blacklight.features.auth.services import AuthService, PermissionService, UserManager


async def get_user_db(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """
    Get user database dependency

    Provides SQLAlchemy user database adapter for FastAPI-Users with OAuth support.

    Args:
        session: Async database session from dependency injection

    Yields:
        SQLAlchemyUserDatabase instance configured with User and OAuthAccount models
    """
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db), db: AsyncSession = Depends(get_db)
):
    """
    Get user manager dependency

    Provides UserManager instance for user-related operations.

    Args:
        user_db: User database from dependency injection
        db: Async database session

    Yields:
        UserManager instance
    """
    yield UserManager(user_db, db)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Get authentication service dependency

    Args:
        db: Async database session

    Returns:
        AuthService instance
    """
    return AuthService(db)


async def get_permission_service(db: AsyncSession = Depends(get_db)) -> PermissionService:
    """
    Get permission service dependency

    Args:
        db: Async database session

    Returns:
        PermissionService instance
    """
    return PermissionService(db)


async def get_settings_repository(db: AsyncSession = Depends(get_db)) -> UserSettingsRepository:
    """
    Get user settings repository dependency

    Args:
        db: Async database session

    Returns:
        UserSettingsRepository instance
    """
    return UserSettingsRepository(db)


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """
    Get user repository dependency

    Args:
        db: Async database session

    Returns:
        UserRepository instance
    """
    return UserRepository(db)


async def get_role_repository(db: AsyncSession = Depends(get_db)) -> RoleRepository:
    """
    Get role repository dependency

    Args:
        db: Async database session

    Returns:
        RoleRepository instance
    """
    return RoleRepository(db)


async def get_permission_repository(db: AsyncSession = Depends(get_db)) -> PermissionRepository:
    """
    Get permission repository dependency

    Args:
        db: Async database session

    Returns:
        PermissionRepository instance
    """
    return PermissionRepository(db)
