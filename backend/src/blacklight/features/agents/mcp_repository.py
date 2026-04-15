"""
MCP Repository Layer

Data access layer for MCP server configurations, agent bindings,
and tool execution audit logs.

Follows the repository pattern for clean separation of data access from business logic.
All methods are async-compatible with SQLAlchemy 2.0.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.blacklight.common.base_repository import BaseRepository
from src.blacklight.features.agents.mcp_models import (
    AgentMCPBinding,
    MCPServerConfig,
    MCPToolExecution,
    MCPTransportEnum,
)


class MCPServerRepository(BaseRepository[MCPServerConfig]):
    """Repository for MCP server configurations"""

    def __init__(self, db: AsyncSession):
        super().__init__(MCPServerConfig, db)

    async def create(  # type: ignore[override]
        self,
        name: str,
        transport: MCPTransportEnum,
        connection_config: dict[str, Any],
        description: str | None = None,
        is_enabled: bool = True,
        requires_approval: bool = False,
        created_by: int | None = None,
    ) -> MCPServerConfig:
        """
        Create a new MCP server configuration.

        Args:
            name: Server name (must be unique)
            transport: Transport type (stdio, HTTP, WebSocket)
            connection_config: Transport-specific configuration dict
            description: Optional server description
            is_enabled: Whether server is enabled (default: True)
            requires_approval: Whether tools require user approval (default: False)
            created_by: User ID of creator (optional)

        Returns:
            Created MCPServerConfig instance
        """
        server = MCPServerConfig(
            id=str(uuid.uuid4()),
            name=name,
            transport=transport,
            connection_config=connection_config,
            description=description,
            is_enabled=1 if is_enabled else 0,
            requires_approval=1 if requires_approval else 0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def get_by_name(self, name: str) -> MCPServerConfig | None:
        """
        Get server configuration by name.

        Args:
            name: Server name

        Returns:
            MCPServerConfig or None if not found
        """
        stmt = select(MCPServerConfig).where(MCPServerConfig.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_enabled_servers(self) -> list[MCPServerConfig]:
        """
        Get all enabled MCP servers.

        Returns:
            List of enabled MCPServerConfig instances
        """
        stmt = select(MCPServerConfig).where(MCPServerConfig.is_enabled == 1)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(  # type: ignore[override]
        self,
        id: str,  # noqa: A002
        **kwargs,
    ) -> MCPServerConfig | None:
        """
        Update MCP server configuration.

        Args:
            id: Server ID
            **kwargs: Fields to update

        Returns:
            Updated MCPServerConfig or None if not found
        """
        server = await self.get_by_id(id)
        if not server:
            return None

        # Convert boolean flags to integers for SQLite compatibility
        if "is_enabled" in kwargs:
            kwargs["is_enabled"] = 1 if kwargs["is_enabled"] else 0
        if "requires_approval" in kwargs:
            kwargs["requires_approval"] = 1 if kwargs["requires_approval"] else 0

        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)

        server.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def delete(self, id: str) -> bool:  # noqa: A002
        """
        Delete MCP server configuration.

        Args:
            id: Server ID

        Returns:
            True if deleted, False if not found
        """
        server = await self.get_by_id(id)
        if not server:
            return False

        await self.db.delete(server)
        await self.db.commit()
        return True


class AgentMCPBindingRepository(BaseRepository[AgentMCPBinding]):
    """Repository for agent-to-MCP-server bindings"""

    def __init__(self, db: AsyncSession):
        super().__init__(AgentMCPBinding, db)

    async def create_binding(
        self,
        agent_id: str,
        server_id: str,
        config_overrides: dict[str, Any] | None = None,
    ) -> AgentMCPBinding:
        """
        Bind an agent to an MCP server.

        Args:
            agent_id: Agent ID
            server_id: MCP server ID
            config_overrides: Optional agent-specific server config

        Returns:
            Created AgentMCPBinding instance
        """
        binding = AgentMCPBinding(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            server_id=server_id,
            config_overrides=config_overrides,
            created_at=datetime.utcnow(),
        )
        self.db.add(binding)
        await self.db.commit()
        await self.db.refresh(binding)
        return binding

    async def get_bindings_for_agent(self, agent_id: str) -> list[AgentMCPBinding]:
        """
        Get all MCP server bindings for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of AgentMCPBinding instances with server data loaded
        """
        stmt = (
            select(AgentMCPBinding)
            .where(AgentMCPBinding.agent_id == agent_id)
            .options(selectinload(AgentMCPBinding.server))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_binding(self, agent_id: str, server_id: str) -> AgentMCPBinding | None:
        """
        Get specific binding between agent and server.

        Args:
            agent_id: Agent ID
            server_id: Server ID

        Returns:
            AgentMCPBinding or None if not found
        """
        stmt = select(AgentMCPBinding).where(
            AgentMCPBinding.agent_id == agent_id,
            AgentMCPBinding.server_id == server_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_binding(self, agent_id: str, server_id: str) -> bool:
        """
        Remove binding between agent and server.

        Args:
            agent_id: Agent ID
            server_id: Server ID

        Returns:
            True if deleted, False if not found
        """
        binding = await self.get_binding(agent_id, server_id)
        if not binding:
            return False

        await self.db.delete(binding)
        await self.db.commit()
        return True

    async def delete_all_bindings_for_agent(self, agent_id: str) -> int:
        """
        Remove all MCP bindings for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Number of bindings deleted
        """
        bindings = await self.get_bindings_for_agent(agent_id)
        count = len(bindings)

        for binding in bindings:
            await self.db.delete(binding)

        await self.db.commit()
        return count


class MCPToolExecutionRepository(BaseRepository[MCPToolExecution]):
    """Repository for MCP tool execution audit logs"""

    def __init__(self, db: AsyncSession):
        super().__init__(MCPToolExecution, db)

    async def log_execution(
        self,
        server_name: str,
        tool_name: str,
        status: str,
        agent_id: str | None = None,
        user_id: int | None = None,
        parameters: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        execution_time_ms: int | None = None,
    ) -> MCPToolExecution:
        """
        Log an MCP tool execution.

        Args:
            server_name: MCP server name
            tool_name: Tool name
            status: Execution status ("success", "error", "timeout")
            agent_id: Agent ID (optional)
            user_id: User ID (optional)
            parameters: Tool input parameters (optional)
            result: Tool output result (optional)
            error_message: Error message if failed (optional)
            execution_time_ms: Execution time in milliseconds (optional)

        Returns:
            Created MCPToolExecution instance
        """
        execution = MCPToolExecution(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            user_id=user_id,
            server_name=server_name,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            status=status,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow(),
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get_executions_for_agent(
        self, agent_id: str, limit: int = 100
    ) -> list[MCPToolExecution]:
        """
        Get recent tool executions for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum number of executions to return

        Returns:
            List of MCPToolExecution instances (most recent first)
        """
        stmt = (
            select(MCPToolExecution)
            .where(MCPToolExecution.agent_id == agent_id)
            .order_by(MCPToolExecution.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_executions_for_server(
        self, server_name: str, limit: int = 100
    ) -> list[MCPToolExecution]:
        """
        Get recent tool executions for an MCP server.

        Args:
            server_name: Server name
            limit: Maximum number of executions to return

        Returns:
            List of MCPToolExecution instances (most recent first)
        """
        stmt = (
            select(MCPToolExecution)
            .where(MCPToolExecution.server_name == server_name)
            .order_by(MCPToolExecution.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_executions(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[MCPToolExecution]:
        """
        Get recent failed tool executions.

        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of executions to return

        Returns:
            List of failed MCPToolExecution instances (most recent first)
        """
        stmt = (
            select(MCPToolExecution)
            .where(MCPToolExecution.status == "error")
            .order_by(MCPToolExecution.timestamp.desc())
            .limit(limit)
        )

        if agent_id:
            stmt = stmt.where(MCPToolExecution.agent_id == agent_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
