"""
Auth feature ORM models

Includes User, Role, Permission, AuditLog, UserSettings, and OAuthAccount models for authentication,
authorization (RBAC), audit logging, user preferences, and OAuth social login.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.blacklight.common.base_repository import Base

if TYPE_CHECKING:
    from src.blacklight.features.agents.models import Agent, Conversation

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("created_at", DateTime, server_default=func.now()),
)


class User(SQLAlchemyBaseUserTable[int], Base):
    """
    User database model

    Extends FastAPI-Users base table with custom fields for RBAC and relationships.
    Uses integer primary key for better performance than UUID.
    """

    __tablename__ = "users"

    # FastAPI-Users provides: id, email, hashed_password, is_active, is_superuser, is_verified
    # We extend with additional fields:

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True, nullable=False)  # type: ignore[assignment]
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)  # type: ignore[assignment]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # type: ignore[assignment]
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # type: ignore[assignment]
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # type: ignore[assignment]

    # Custom fields
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=True
    )  # Foreign key to roles table
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    role: Mapped["Role | None"] = relationship("Role", back_populates="users", lazy="selectin")
    settings: Mapped["UserSettings | None"] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role.name if self.role else 'None'})>"


class UserSettings(Base):
    """
    User Settings database model

    Stores user preferences including theme, custom prompts, and other settings.
    One-to-one relationship with User model.
    """

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Theme preference: 'light', 'dark', or 'system'
    theme: Mapped[str] = mapped_column(String(20), default="system", nullable=False)

    # Custom prompts and preferences stored as JSON
    # Example: {"system_prompt": "...", "agent_instructions": "..."}
    custom_prompts: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Additional user preferences
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings", uselist=False)

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, theme={self.theme})>"


class OAuthAccount(Base):
    """
    OAuth Account database model

    Stores OAuth provider account linkages for users. Each user can link multiple
    OAuth providers (Google, Microsoft, GitHub, etc.) for social login.
    One OAuth account per provider per user (enforced by unique constraint).
    """

    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # OAuth provider info
    oauth_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # "google", "github", etc.
    account_id: Mapped[str] = mapped_column(String(320), nullable=False, index=True)  # Provider's user ID
    account_email: Mapped[str] = mapped_column(String(320), nullable=False)  # Email from provider

    # OAuth tokens (stored for token refresh)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    def __repr__(self):
        return f"<OAuthAccount(user_id={self.user_id}, provider={self.oauth_name}, account={self.account_email})>"


class Role(Base):
    """
    Role database model for RBAC

    Defines user roles (e.g., superadmin, admin, user, guest) with associated permissions.
    Roles form a hierarchy: superadmin > admin > user > guest
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g., "admin", "user"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """
    Permission database model for RBAC

    Defines fine-grained permissions using resource:action format.
    Examples: "agents:create", "agents:read", "agents:delete", "users:manage"
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # e.g., "agents:create"
    resource: Mapped[str] = mapped_column(String(50), index=True)  # e.g., "agents", "users"
    action: Mapped[str] = mapped_column(
        String(50), index=True
    )  # e.g., "create", "read", "update", "delete"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class AuditLog(Base):
    """
    Audit Log database model

    Tracks security-relevant events like login attempts, permission denials,
    role changes, and other security-sensitive operations.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Nullable for failed login attempts
    event_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # e.g., "login", "logout", "permission_denied"
    event_action: Mapped[str] = mapped_column(
        String(100)
    )  # e.g., "login_success", "login_failed", "agents:create_denied"
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)  # Browser/client info
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Additional event context
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"
