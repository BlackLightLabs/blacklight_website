"""
MCP Service Layer

Business logic for MCP server management, tool discovery, and smart suggestions.

Key features:
- Initialize MCP client with database-configured servers
- Load tools from MCP servers into tool registry
- Smart MCP server suggestions based on user requirements
- Integration with agent builder service
"""

import re
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.mcp_client import (
    MCPClientManager,
    MCPServerConfig,
    MCPTransportType,
    get_mcp_client_manager,
)
from src.blacklight.features.agents.mcp_models import MCPTransportEnum
from src.blacklight.features.agents.mcp_repository import MCPServerRepository
from src.blacklight.features.agents.tools.registry import ToolRegistry, get_tool_registry

logger = structlog.get_logger(__name__)


# Smart suggestion patterns: keyword -> server recommendations
MCP_SERVER_SUGGESTIONS = {
    "browser": ["playwright", "puppeteer", "selenium"],
    "web": ["playwright", "puppeteer", "selenium"],
    "automation": ["playwright", "puppeteer"],
    "scraping": ["playwright", "puppeteer"],
    "screenshot": ["playwright"],
    "testing": ["playwright", "selenium"],
    "database": ["postgres", "mysql", "mongodb"],
    "sql": ["postgres", "mysql", "sqlite"],
    "api": ["rest-api", "graphql", "openapi"],
    "file": ["filesystem", "s3", "google-drive"],
    "storage": ["s3", "google-drive", "dropbox"],
    "email": ["gmail", "sendgrid", "mailgun"],
    "calendar": ["google-calendar", "outlook"],
    "github": ["github"],
    "git": ["github", "gitlab", "bitbucket"],
    "slack": ["slack"],
    "discord": ["discord"],
    "documentation": ["context7"],
    "docs": ["context7"],
    "search": ["google-search", "bing-search"],
}


class MCPService:
    """
    Service for managing MCP servers and tool discovery.

    Responsibilities:
    - Initialize MCP client from database configuration
    - Load tools from MCP servers into tool registry
    - Suggest relevant MCP servers based on user requirements
    - Generate MCP-aware tool catalogs for LLM prompts
    """

    def __init__(
        self,
        db: AsyncSession,
        mcp_client: MCPClientManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        """
        Initialize MCP service.

        Args:
            db: Database session
            mcp_client: MCP client manager (defaults to global instance)
            tool_registry: Tool registry (defaults to global instance)
        """
        self.db = db
        self.mcp_client = mcp_client or get_mcp_client_manager()
        self.tool_registry = tool_registry or get_tool_registry()
        self.mcp_repo = MCPServerRepository(db)

    async def initialize_mcp_servers(self) -> dict[str, int]:
        """
        Initialize MCP client with servers from database.

        Loads enabled MCP server configurations from database,
        initializes the MCP client, and registers tools in the registry.

        Returns:
            Dict mapping server names to tool counts
        """
        try:
            # Load enabled servers from database
            db_servers = await self.mcp_repo.get_enabled_servers()

            if not db_servers:
                logger.info("no_mcp_servers_configured")
                return {}

            # Convert database models to MCPServerConfig
            server_configs = []
            for db_server in db_servers:
                try:
                    config = MCPServerConfig(
                        name=db_server.name,
                        transport=MCPTransportType(db_server.transport.value),
                        enabled=bool(db_server.is_enabled),
                        requires_approval=bool(db_server.requires_approval),
                        **db_server.connection_config,  # Unpack transport-specific config
                    )
                    server_configs.append(config)
                except Exception as e:
                    logger.error(
                        "mcp_server_config_conversion_failed",
                        server=db_server.name,
                        error=str(e),
                    )
                    continue

            # Initialize MCP client
            await self.mcp_client.initialize(server_configs)

            # Load tools from each server and register them
            tool_counts = {}
            for server_config in server_configs:
                try:
                    tools = await self.mcp_client.get_tools(
                        server_config.name, use_cache=False
                    )
                    if tools:
                        self.tool_registry.register_mcp_server(
                            server_config.name,
                            tools,
                            requires_approval=server_config.requires_approval,
                        )
                        tool_counts[server_config.name] = len(tools)
                        logger.info(
                            "mcp_server_tools_loaded",
                            server=server_config.name,
                            tool_count=len(tools),
                        )
                    else:
                        logger.warning(
                            "mcp_server_no_tools",
                            server=server_config.name,
                        )
                        tool_counts[server_config.name] = 0
                except Exception as e:
                    logger.error(
                        "mcp_server_tool_loading_failed",
                        server=server_config.name,
                        error=str(e),
                        exc_info=True,
                    )
                    tool_counts[server_config.name] = 0

            logger.info(
                "mcp_initialization_complete",
                server_count=len(server_configs),
                total_tools=sum(tool_counts.values()),
            )

            return tool_counts

        except Exception as e:
            logger.error("mcp_initialization_failed", error=str(e), exc_info=True)
            return {}

    async def suggest_mcp_servers(self, user_requirements: str) -> list[dict[str, Any]]:
        """
        Suggest relevant MCP servers based on user requirements.

        Analyzes the user's description and suggests MCP servers that
        might be useful for their agent.

        Args:
            user_requirements: User's description of what they want to build

        Returns:
            List of suggestions with format:
            [
                {
                    "server_name": "playwright",
                    "reason": "For browser automation and web testing",
                    "available": True,
                    "tool_count": 15
                }
            ]
        """
        # Normalize input
        requirements_lower = user_requirements.lower()

        # Find matching keywords
        suggestions = []
        matched_servers = set()

        for keyword, server_names in MCP_SERVER_SUGGESTIONS.items():
            # Check if keyword appears in requirements
            if re.search(r'\b' + re.escape(keyword) + r'\b', requirements_lower):
                for server_name in server_names:
                    if server_name not in matched_servers:
                        matched_servers.add(server_name)

                        # Check if server is available
                        available = server_name in self.tool_registry.list_mcp_servers()
                        tool_count = (
                            len(self.tool_registry.get_mcp_tools(server_name))
                            if available
                            else 0
                        )

                        # Generate reason
                        reason = self._get_suggestion_reason(server_name, keyword)

                        suggestions.append(
                            {
                                "server_name": server_name,
                                "reason": reason,
                                "available": available,
                                "tool_count": tool_count,
                            }
                        )

        logger.info(
            "mcp_suggestions_generated",
            requirements_preview=user_requirements[:100],
            suggestion_count=len(suggestions),
        )

        return suggestions

    def _get_suggestion_reason(self, server_name: str, matched_keyword: str) -> str:
        """
        Generate human-readable reason for MCP server suggestion.

        Args:
            server_name: Name of the MCP server
            matched_keyword: Keyword that triggered the suggestion

        Returns:
            Human-readable reason string
        """
        reasons = {
            "playwright": "For browser automation, web scraping, and testing",
            "puppeteer": "For headless browser control and web automation",
            "selenium": "For cross-browser web testing and automation",
            "postgres": "For PostgreSQL database queries and operations",
            "mysql": "For MySQL database access",
            "mongodb": "For MongoDB document database operations",
            "context7": "For accessing up-to-date library documentation",
            "github": "For GitHub repository and issue management",
            "slack": "For Slack messaging and workspace integration",
            "gmail": "For email sending and inbox management",
            "google-calendar": "For calendar event management",
            "s3": "For AWS S3 file storage operations",
            "google-drive": "For Google Drive file management",
        }

        return reasons.get(
            server_name,
            f"For {matched_keyword}-related functionality",
        )

    async def get_mcp_tool_catalog_for_prompt(self) -> str:
        """
        Generate formatted MCP tool catalog for LLM system prompts.

        Returns:
            Formatted string describing available MCP servers and their tools
        """
        mcp_servers = self.tool_registry.list_mcp_servers()

        if not mcp_servers:
            return "No MCP servers currently available."

        lines = ["## Available MCP Servers", ""]
        lines.append(
            "You can use tools from these external MCP (Model Context Protocol) servers:"
        )
        lines.append("")

        for server_name in mcp_servers:
            tools = self.tool_registry.get_mcp_tools(server_name)
            if tools:
                lines.append(f"### {server_name} ({len(tools)} tools)")
                lines.append("")
                for tool in tools[:5]:  # Show first 5 tools per server
                    lines.append(f"  - **{tool.name}**: {tool.description}")
                if len(tools) > 5:
                    lines.append(f"  - ... and {len(tools) - 5} more tools")
                lines.append("")

        lines.append("**To use MCP tools in an agent:**")
        lines.append('1. Add to `mcp_servers`: [{"name": "server_name", "enabled": true}]')
        lines.append('2. Reference MCP tools in `tools` list with `"transport": "mcp"`')
        lines.append("")

        return "\n".join(lines)

    async def reload_server_tools(self, server_name: str) -> int:
        """
        Reload tools from a specific MCP server.

        Args:
            server_name: Name of the server to reload

        Returns:
            Number of tools loaded, or 0 if failed
        """
        try:
            # Invalidate cache and reload
            await self.mcp_client.reload_server(server_name)
            tools = await self.mcp_client.get_tools(server_name, use_cache=False)

            if tools:
                # Get server config to check approval requirement
                server_config = await self.mcp_repo.get_by_name(server_name)
                requires_approval = bool(server_config.requires_approval) if server_config else False

                # Re-register tools
                self.tool_registry.register_mcp_server(
                    server_name,
                    tools,
                    requires_approval=requires_approval,
                )

                logger.info(
                    "mcp_server_tools_reloaded",
                    server=server_name,
                    tool_count=len(tools),
                )
                return len(tools)
            else:
                logger.warning("mcp_server_reload_no_tools", server=server_name)
                return 0

        except Exception as e:
            logger.error(
                "mcp_server_reload_failed",
                server=server_name,
                error=str(e),
                exc_info=True,
            )
            return 0
