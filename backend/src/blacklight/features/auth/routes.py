"""
Authentication and User Settings Routes

This module provides a consolidated set of endpoints for:
- User authentication (login, logout, register)
- User management (get/update current user)
- User settings (theme, custom prompts, preferences)

All routes are integrated with FastAPI-Users for secure authentication
and RBAC permission checking.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.database import get_db
from src.blacklight.common.settings import settings as app_settings
from src.blacklight.features.auth.dependencies import (
    get_settings_repository,
    get_user_manager,
)
from src.blacklight.features.auth.models import User
from src.blacklight.features.auth.oauth import get_enabled_oauth_clients, get_enabled_provider_names
from src.blacklight.features.auth.repositories import UserSettingsRepository
from src.blacklight.features.auth.schemas import (
    ConnectedAccountsResponse,
    ConnectedOAuthAccount,
    OAuthProviderInfo,
    OAuthProvidersResponse,
    SettingsRead,
    SettingsUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.blacklight.features.auth.utils import auth_backend

# Initialize FastAPI Users
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Create main router
router = APIRouter()

# Include auth routes (login, logout)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Include registration routes
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Include user routes (get/update current user)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Dynamically register OAuth routers for enabled providers
if app_settings.oauth2_enabled:
    oauth_clients = get_enabled_oauth_clients()
    for provider_name, oauth_client in oauth_clients.items():
        router.include_router(
            fastapi_users.get_oauth_router(
                oauth_client,
                auth_backend,
                app_settings.jwt_secret,
                # No redirect_url parameter - let OAuth provider redirect to backend callback
                # The custom CookieRedirectTransport will redirect to frontend after auth
                # Auto-verify OAuth users (they've been authenticated by the provider)
                is_verified_by_default=True,
                # Associate OAuth accounts with existing users if email matches
                associate_by_email=True,
            ),
            prefix=f"/auth/{provider_name}",
            tags=["auth", "oauth"],
        )

# Export current_user dependency for protecting routes
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


# Settings Routes
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("/me", response_model=SettingsRead)
async def get_my_settings(
    current_user: User = Depends(current_active_user),
    settings_repo: UserSettingsRepository = Depends(get_settings_repository),
):
    """
    Get current user's settings

    Returns user settings or creates default settings if none exist.
    """
    settings = await settings_repo.get_or_create(current_user.id)
    return settings


@settings_router.patch("/me", response_model=SettingsRead)
async def update_my_settings(
    settings_update: SettingsUpdate,
    current_user: User = Depends(current_active_user),
    settings_repo: UserSettingsRepository = Depends(get_settings_repository),
):
    """
    Update current user's settings

    Allows partial updates of theme, custom_prompts, and preferences.
    """
    # Ensure settings exist before updating
    await settings_repo.get_or_create(current_user.id)

    # Update settings
    updated_settings = await settings_repo.update_settings(
        user_id=current_user.id,
        theme=settings_update.theme,
        custom_prompts=settings_update.custom_prompts,
        preferences=settings_update.preferences,
    )

    if not updated_settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")

    return updated_settings


@settings_router.patch("/me/theme", response_model=SettingsRead)
async def update_my_theme(
    theme: str,
    current_user: User = Depends(current_active_user),
    settings_repo: UserSettingsRepository = Depends(get_settings_repository),
):
    """
    Update current user's theme preference

    Args:
        theme: Theme name ('light', 'dark', or 'system')
    """
    # Validate theme
    if theme not in ["light", "dark", "system"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Theme must be 'light', 'dark', or 'system'",
        )

    # Ensure settings exist before updating
    await settings_repo.get_or_create(current_user.id)

    # Update theme
    updated_settings = await settings_repo.update_theme(current_user.id, theme)

    if not updated_settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")

    return updated_settings


# Include settings routes in main router
router.include_router(settings_router)


# OAuth Routes
oauth_router = APIRouter(prefix="/auth/oauth", tags=["auth", "oauth"])


@oauth_router.get("/providers", response_model=OAuthProvidersResponse)
async def get_oauth_providers():
    """
    Get list of enabled OAuth providers.

    Returns configuration for all enabled OAuth providers (Google, GitHub, Microsoft, OIDC).
    Frontend uses this to dynamically render OAuth login buttons.

    Returns:
        OAuthProvidersResponse with global OAuth status and provider list
    """
    enabled_providers = get_enabled_provider_names()

    # Map provider names to display names
    provider_display_names = {
        "google": "Google",
        "github": "GitHub",
        "microsoft": "Microsoft",
        app_settings.oidc_provider_name.lower(): app_settings.oidc_provider_name,
    }

    providers = []
    for provider_name in enabled_providers:
        providers.append(
            OAuthProviderInfo(
                name=provider_name,
                display_name=provider_display_names.get(provider_name, provider_name.title()),
                enabled=True,
                authorize_url=f"/api/auth/{provider_name}/authorize",
            )
        )

    return OAuthProvidersResponse(
        enabled=app_settings.oauth2_enabled and len(enabled_providers) > 0,
        providers=providers,
    )


@oauth_router.get("/accounts", response_model=ConnectedAccountsResponse)
async def get_connected_oauth_accounts(
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of OAuth accounts connected to the current user.

    Returns all OAuth accounts linked to the user's account, along with
    available providers that can be connected.

    Returns:
        ConnectedAccountsResponse with connected accounts and available providers
    """
    from sqlalchemy import select
    from src.blacklight.features.auth.models import OAuthAccount

    # Get connected OAuth accounts
    stmt = select(OAuthAccount).where(OAuthAccount.user_id == current_user.id)
    result = await db.execute(stmt)
    oauth_accounts = result.scalars().all()

    # Map provider names to display names
    provider_display_names = {
        "google": "Google",
        "github": "GitHub",
        "microsoft": "Microsoft",
        app_settings.oidc_provider_name.lower(): app_settings.oidc_provider_name,
    }

    # Build connected accounts list
    connected_accounts = [
        ConnectedOAuthAccount(
            id=account.id,
            provider=account.oauth_name,
            display_name=provider_display_names.get(account.oauth_name, account.oauth_name.title()),
            account_email=account.account_email,
            connected_at=account.created_at,
        )
        for account in oauth_accounts
    ]

    # Get available providers (enabled providers not yet connected)
    enabled_providers = get_enabled_provider_names()
    connected_provider_names = {account.oauth_name for account in oauth_accounts}

    available_providers = [
        OAuthProviderInfo(
            name=provider_name,
            display_name=provider_display_names.get(provider_name, provider_name.title()),
            enabled=True,
            authorize_url=f"/api/auth/{provider_name}/authorize",
        )
        for provider_name in enabled_providers
        if provider_name not in connected_provider_names
    ]

    return ConnectedAccountsResponse(
        accounts=connected_accounts,
        available_providers=available_providers,
    )


@oauth_router.delete("/accounts/{oauth_account_id}")
async def disconnect_oauth_account(
    oauth_account_id: int,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect an OAuth account from the current user.

    Args:
        oauth_account_id: ID of the OAuth account to disconnect

    Returns:
        Success message

    Raises:
        HTTPException: If account not found or doesn't belong to current user
    """
    from sqlalchemy import delete, select
    from src.blacklight.features.auth.models import OAuthAccount

    # Verify the OAuth account exists and belongs to the current user
    stmt = select(OAuthAccount).where(
        OAuthAccount.id == oauth_account_id,
        OAuthAccount.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    oauth_account = result.scalar_one_or_none()

    if not oauth_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth account not found or does not belong to you",
        )

    # Check if user has a password or other OAuth accounts
    # Don't allow disconnecting the last authentication method
    stmt = select(OAuthAccount).where(OAuthAccount.user_id == current_user.id)
    result = await db.execute(stmt)
    oauth_accounts_count = len(result.scalars().all())

    if oauth_accounts_count == 1 and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect your last authentication method. Please set a password first.",
        )

    # Delete the OAuth account
    stmt = delete(OAuthAccount).where(OAuthAccount.id == oauth_account_id)
    await db.execute(stmt)
    await db.commit()

    return {"message": "OAuth account disconnected successfully"}


# Include OAuth routes in main router
router.include_router(oauth_router)
