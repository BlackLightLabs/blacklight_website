"""
MCP Integration Models

Database models for Model Context Protocol (MCP) server configuration,
agent bindings, and tool execution audit logging.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.blacklight.common.base_repository import Base

if TYPE_CHECKING:
    from src.blacklight.features.agents.models import Agent
    from src.blacklight.features.auth.models import User


class MCPTransportEnum(str, enum.Enum):
    """MCP server transport types"""

    STDIO = "STDIO"
    STREAMABLE_HTTP = "STREAMABLE_HTTP"
    SSE = "SSE"
    WEBSOCKET = "WEBSOCKET"


class MCPServerConfig(Base):
    """
    MCP Server Configuration model

    Stores configuration for external MCP servers that agents can connect to.
    Supports multiple transport types (stdio, HTTP, WebSocket).
    """

    __tablename__ = "mcp_server_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    transport: Mapped[MCPTransportEnum] = mapped_column(
        Enum(MCPTransportEnum, name="mcp_transport_type")
    )
    connection_config: Mapped[dict] = mapped_column(
        JSON
    )  # Transport-specific config (command, args, url, headers, etc.)
    is_enabled: Mapped[int] = mapped_column(
        Integer, default=1, index=True
    )  # 1=enabled, 0=disabled (SQLite compat)
    requires_approval: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 1=requires approval, 0=no approval
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    creator: Mapped["User | None"] = relationship("User")
    bindings: Mapped[list["AgentMCPBinding"]] = relationship(
        "AgentMCPBinding", back_populates="server", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MCPServerConfig(id={self.id}, name={self.name}, transport={self.transport}, enabled={bool(self.is_enabled)})>"


class AgentMCPBinding(Base):
    """
    Agent MCP Binding model

    Many-to-many relationship between agents and MCP servers.
    Tracks which MCP servers each agent is allowed to use.
    """

    __tablename__ = "agent_mcp_bindings"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), index=True)
    server_id: Mapped[str] = mapped_column(String, ForeignKey("mcp_server_configs.id"), index=True)
    config_overrides: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Agent-specific server config overrides
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", backref="mcp_bindings")
    server: Mapped["MCPServerConfig"] = relationship("MCPServerConfig", back_populates="bindings")

    def __repr__(self):
        return f"<AgentMCPBinding(id={self.id}, agent_id={self.agent_id}, server_id={self.server_id})>"


class MCPToolExecution(Base):
    """
    MCP Tool Execution model

    Audit log of MCP tool invocations by agents and users.
    Tracks tool name, parameters, results, and performance metrics.
    """

    __tablename__ = "mcp_tool_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    server_name: Mapped[str] = mapped_column(String(100), index=True)
    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), index=True
    )  # "success", "error", "timeout"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Relationships
    agent: Mapped["Agent | None"] = relationship("Agent")
    user: Mapped["User | None"] = relationship("User")

    def __repr__(self):
        return f"<MCPToolExecution(id={self.id}, server={self.server_name}, tool={self.tool_name}, status={self.status})>"
