"""
MCP Client Manager

Manages connections to MCP (Model Context Protocol) servers and provides
tools to agents. Supports stdio, HTTP, and WebSocket transports.

Key features:
- Dynamic MCP server discovery and connection
- Connection pooling and lifecycle management
- Tool loading and caching
- Error handling with circuit breaker pattern
- Support for multiple transport types (stdio, HTTP, WebSocket)

Architecture:
- Uses langchain-mcp-adapters for MCP integration
- Integrates with existing error handling and retry logic
- Thread-safe singleton pattern for global client manager
"""

import asyncio
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import BaseModel

from src.blacklight.common.circuit_breaker import CircuitBreaker
from src.blacklight.common.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


class MCPTransportType(str, Enum):
    """MCP server transport types"""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPServerConfig(BaseModel):
    """
    Configuration for an MCP server connection.

    Supports multiple transport types with transport-specific config.
    """

    name: str
    transport: MCPTransportType
    enabled: bool = True
    requires_approval: bool = False

    # stdio transport config
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None

    # HTTP/SSE transport config
    url: str | None = None
    headers: dict[str, str] | None = None
    timeout: float | None = None
    sse_read_timeout: float | None = None

    # WebSocket transport config (uses url from above)

    def to_client_config(self) -> dict[str, Any]:
        """
        Convert to MultiServerMCPClient config format.

        Returns:
            Dict suitable for MultiServerMCPClient initialization
        """
        config: dict[str, Any] = {
            "transport": self.transport.value,
        }

        if self.transport == MCPTransportType.STDIO:
            if not self.command:
                raise ValueError(f"stdio transport requires 'command' for server '{self.name}'")
            config["command"] = self.command
            if self.args:
                config["args"] = self.args
            if self.env:
                config["env"] = self.env
            if self.cwd:
                config["cwd"] = self.cwd

        elif self.transport in [MCPTransportType.STREAMABLE_HTTP, MCPTransportType.SSE]:
            if not self.url:
                raise ValueError(
                    f"{self.transport} transport requires 'url' for server '{self.name}'"
                )
            config["url"] = self.url
            if self.headers:
                config["headers"] = self.headers
            if self.timeout:
                config["timeout"] = self.timeout
            if self.sse_read_timeout:
                config["sse_read_timeout"] = self.sse_read_timeout

        elif self.transport == MCPTransportType.WEBSOCKET:
            if not self.url:
                raise ValueError(f"websocket transport requires 'url' for server '{self.name}'")
            config["url"] = self.url

        return config


class MCPToolCache:
    """
    Cache for MCP tools with TTL-based expiration.

    Reduces overhead of repeatedly loading tool schemas from MCP servers.
    """

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self._cache: dict[str, tuple[list[BaseTool], datetime]] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, server_name: str) -> list[BaseTool] | None:
        """Get cached tools if not expired"""
        async with self._lock:
            if server_name in self._cache:
                tools, cached_at = self._cache[server_name]
                if datetime.utcnow() - cached_at < timedelta(seconds=self._ttl_seconds):
                    logger.debug("mcp_cache_hit", server=server_name)
                    return tools
                else:
                    # Expired
                    logger.debug("mcp_cache_expired", server=server_name)
                    del self._cache[server_name]
        return None

    async def set(self, server_name: str, tools: list[BaseTool]):
        """Cache tools with current timestamp"""
        async with self._lock:
            self._cache[server_name] = (tools, datetime.utcnow())
            logger.debug("mcp_cache_set", server=server_name, tool_count=len(tools))

    async def invalidate(self, server_name: str | None = None):
        """Invalidate cache for specific server or all servers"""
        async with self._lock:
            if server_name:
                self._cache.pop(server_name, None)
                logger.debug("mcp_cache_invalidated", server=server_name)
            else:
                self._cache.clear()
                logger.debug("mcp_cache_cleared")


class MCPClientManager:
    """
    Manager for MCP server connections and tool loading.

    Provides high-level interface for:
    - Connecting to MCP servers
    - Loading tools from servers (with caching)
    - Managing server lifecycle
    - Error handling and circuit breaking

    Thread-safe singleton pattern - use get_mcp_client_manager() to access.
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize MCP client manager.

        Args:
            cache_ttl_seconds: Tool cache TTL in seconds (default: 5 minutes)
        """
        self._client: MultiServerMCPClient | None = None
        self._servers: dict[str, MCPServerConfig] = {}
        self._cache = MCPToolCache(ttl_seconds=cache_ttl_seconds)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        logger.info("mcp_client_manager_initialized", cache_ttl=cache_ttl_seconds)

    async def initialize(self, server_configs: list[MCPServerConfig]):
        """
        Initialize MCP client with server configurations.

        Creates MultiServerMCPClient instance and prepares for tool loading.

        Args:
            server_configs: List of MCP server configurations

        Raises:
            ExternalServiceError: If initialization fails
        """
        async with self._lock:
            if self._initialized:
                logger.warning("mcp_client_already_initialized")
                return

            try:
                # Filter enabled servers
                enabled_servers = [s for s in server_configs if s.enabled]
                if not enabled_servers:
                    logger.warning("no_enabled_mcp_servers")
                    self._initialized = True
                    return

                # Build client config
                client_config = {}
                for server in enabled_servers:
                    try:
                        client_config[server.name] = server.to_client_config()
                        self._servers[server.name] = server
                        # Initialize circuit breaker for this server
                        self._circuit_breakers[server.name] = CircuitBreaker(
                            name=f"mcp_server_{server.name}",
                            failure_threshold=5,
                            recovery_timeout=60.0,
                        )
                    except ValueError as e:
                        logger.error(
                            "invalid_mcp_server_config",
                            server=server.name,
                            error=str(e),
                        )
                        continue

                if not client_config:
                    logger.warning("no_valid_mcp_servers")
                    self._initialized = True
                    return

                # Create client
                self._client = MultiServerMCPClient(client_config)
                self._initialized = True

                logger.info(
                    "mcp_client_initialized",
                    server_count=len(client_config),
                    servers=list(client_config.keys()),
                )

            except Exception as e:
                logger.error("mcp_client_initialization_failed", error=str(e), exc_info=True)
                raise ExternalServiceError(
                    service_name="mcp_client",
                    message=f"Failed to initialize MCP client: {e}",
                    details={"operation": "initialize"},
                    original_error=e,
                ) from e

    async def get_tools(
        self, server_name: str, use_cache: bool = True
    ) -> list[BaseTool] | None:
        """
        Get tools from a specific MCP server.

        Args:
            server_name: Name of the MCP server
            use_cache: Whether to use cached tools (default: True)

        Returns:
            List of LangChain tools, or None if server not found/failed

        Raises:
            ExternalServiceError: If tool loading fails critically
        """
        if not self._initialized:
            logger.warning("mcp_client_not_initialized", server=server_name)
            return None

        if not self._client:
            logger.warning("mcp_client_not_available", server=server_name)
            return None

        if server_name not in self._servers:
            logger.warning("mcp_server_not_found", server=server_name)
            return None

        # Check cache first
        if use_cache:
            cached_tools = await self._cache.get(server_name)
            if cached_tools is not None:
                return cached_tools

        # Check circuit breaker
        circuit_breaker = self._circuit_breakers.get(server_name)
        if circuit_breaker and circuit_breaker.is_open:
            logger.warning(
                "mcp_circuit_breaker_open",
                server=server_name,
                state=circuit_breaker.state,
            )
            return None

        try:
            # Load tools from MCP server
            logger.info("loading_mcp_tools", server=server_name)

            async with self._client.session(server_name) as session:
                tools = await load_mcp_tools(session)

            logger.info(
                "mcp_tools_loaded",
                server=server_name,
                tool_count=len(tools),
                tools=[t.name for t in tools],
            )

            # Cache tools
            await self._cache.set(server_name, tools)

            # Record success for circuit breaker
            if circuit_breaker:
                await circuit_breaker._record_success()

            return tools

        except Exception as e:
            logger.error(
                "mcp_tool_loading_failed",
                server=server_name,
                error=str(e),
                exc_info=True,
            )

            # Record failure for circuit breaker
            if circuit_breaker:
                await circuit_breaker._record_failure(e)

            # Don't raise - return None to allow graceful degradation
            return None

    async def get_all_tools(self, use_cache: bool = True) -> dict[str, list[BaseTool]]:
        """
        Get tools from all enabled MCP servers.

        Args:
            use_cache: Whether to use cached tools (default: True)

        Returns:
            Dict mapping server names to tool lists
        """
        all_tools = {}
        for server_name in self._servers.keys():
            tools = await self.get_tools(server_name, use_cache=use_cache)
            if tools:
                all_tools[server_name] = tools
        return all_tools

    async def reload_server(self, server_name: str):
        """
        Reload tools from a specific server (invalidate cache).

        Args:
            server_name: Name of the server to reload
        """
        await self._cache.invalidate(server_name)
        logger.info("mcp_server_reloaded", server=server_name)

    async def shutdown(self):
        """
        Shutdown MCP client and cleanup resources.

        Should be called during application shutdown.
        """
        async with self._lock:
            if self._client:
                # MultiServerMCPClient doesn't have explicit shutdown
                # Sessions are context-managed
                self._client = None
                logger.info("mcp_client_shutdown")
            self._servers.clear()
            self._circuit_breakers.clear()
            await self._cache.invalidate()
            self._initialized = False

    def get_server_config(self, server_name: str) -> MCPServerConfig | None:
        """Get configuration for a specific server"""
        return self._servers.get(server_name)

    def list_servers(self) -> list[str]:
        """List all configured server names"""
        return list(self._servers.keys())

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self._initialized


# Global singleton instance
_mcp_client_manager: MCPClientManager | None = None


def get_mcp_client_manager() -> MCPClientManager:
    """
    Get the global MCP client manager instance.

    Returns:
        Global MCPClientManager singleton
    """
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager


def load_mcp_config_from_env() -> list[MCPServerConfig]:
    """
    Load MCP server configurations from environment variables.

    Expected format:
    MCP_SERVERS='[{"name": "weather", "transport": "stdio", "command": "python", "args": ["server.py"]}]'

    Returns:
        List of MCPServerConfig instances
    """
    import json

    mcp_servers_json = os.getenv("MCP_SERVERS", "[]")
    try:
        servers_data = json.loads(mcp_servers_json)
        configs = [MCPServerConfig(**server) for server in servers_data]
        logger.info("mcp_config_loaded_from_env", server_count=len(configs))
        return configs
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("mcp_config_parse_error", error=str(e))
        return []
