"""
Auth feature Pydantic schemas

Includes schemas for User operations (read, create, update) and UserSettings operations.
"""

from datetime import datetime
from typing import Any

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# User Schemas
# ============================================================================


class UserRead(schemas.BaseUser[int]):
    """
    Schema for reading user data

    Extends FastAPI-Users BaseUser with custom fields.
    """

    id: int
    email: EmailStr
    full_name: str | None = None
    role_id: int | None = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False


class UserCreate(schemas.BaseUserCreate):
    """
    Schema for creating a new user

    Requires email and password, with optional full_name.
    """

    email: EmailStr
    password: str
    full_name: str | None = None
    role_id: int | None = None
    is_active: bool | None = True
    is_superuser: bool | None = False
    is_verified: bool | None = False


class UserUpdate(schemas.BaseUserUpdate):
    """
    Schema for updating user information

    All fields are optional.
    """

    email: EmailStr | None = None
    password: str | None = None
    full_name: str | None = None
    role_id: int | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None


# ============================================================================
# UserSettings Schemas
# ============================================================================


class SettingsBase(BaseModel):
    """Base schema for settings with common fields"""

    theme: str | None = Field(None, pattern="^(light|dark|system)$")
    custom_prompts: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None


class SettingsCreate(SettingsBase):
    """
    Schema for creating new user settings

    All fields are optional, defaults will be applied if not provided.
    """

    pass


class SettingsUpdate(BaseModel):
    """
    Schema for updating user settings

    All fields are optional to allow partial updates.
    """

    theme: str | None = Field(None, pattern="^(light|dark|system)$")
    custom_prompts: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None


class SettingsRead(SettingsBase):
    """
    Schema for reading user settings

    Includes all fields from the database model.
    """

    id: int
    user_id: int
    theme: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Permission Schemas
# ============================================================================


class PermissionRead(BaseModel):
    """Schema for reading permission data"""

    id: int
    name: str
    resource: str
    action: str
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Role Schemas
# ============================================================================


class RoleBase(BaseModel):
    """Base schema for roles with common fields"""

    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class RoleCreate(RoleBase):
    """Schema for creating a new role"""

    permission_ids: list[int] | None = None


class RoleUpdate(BaseModel):
    """Schema for updating role information"""

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    permission_ids: list[int] | None = None


class RoleRead(RoleBase):
    """Schema for reading role data"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleRead):
    """Schema for reading role data with permissions"""

    permissions: list[PermissionRead] = []


# ============================================================================
# Admin User Schemas (with role details)
# ============================================================================


class UserWithRole(UserRead):
    """
    Schema for reading user data with role details

    Includes the role name and permissions inherited from the role.
    """

    role: RoleRead | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """
    Simplified schema for user list display

    Optimized for table/list views with essential fields only.
    """

    id: int
    email: EmailStr
    full_name: str | None = None
    role_id: int | None = None
    role_name: str | None = None
    is_active: bool
    is_superuser: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Admin Operation Schemas
# ============================================================================


class AssignRoleRequest(BaseModel):
    """Schema for assigning a role to a user"""

    user_id: int
    role_id: int


class UpdateUserRoleRequest(BaseModel):
    """Schema for updating a user's role"""

    role_id: int


# ============================================================================
# OAuth Schemas
# ============================================================================


class OAuthProviderInfo(BaseModel):
    """Schema for OAuth provider information"""

    name: str = Field(..., description="Provider internal name (e.g., 'google', 'github')")
    display_name: str = Field(..., description="Provider display name (e.g., 'Google', 'GitHub')")
    enabled: bool = Field(..., description="Whether this provider is enabled")
    authorize_url: str = Field(..., description="URL to initiate OAuth flow")


class OAuthProvidersResponse(BaseModel):
    """Schema for OAuth providers list response"""

    enabled: bool = Field(..., description="Whether OAuth2 is globally enabled")
    providers: list[OAuthProviderInfo] = Field(..., description="List of configured OAuth providers")


class ConnectedOAuthAccount(BaseModel):
    """Schema for connected OAuth account information"""

    id: int = Field(..., description="OAuth account ID")
    provider: str = Field(..., description="Provider name (e.g., 'google', 'github')")
    display_name: str = Field(..., description="Provider display name (e.g., 'Google', 'GitHub')")
    account_email: str = Field(..., description="Email associated with this OAuth account")
    connected_at: datetime = Field(..., description="When this account was first connected")

    class Config:
        from_attributes = True


class ConnectedAccountsResponse(BaseModel):
    """Schema for list of connected OAuth accounts"""

    accounts: list[ConnectedOAuthAccount] = Field(..., description="List of connected OAuth accounts")
    available_providers: list[OAuthProviderInfo] = Field(..., description="Providers available to connect")
