"""
Tool Registry

Central registry for all tools available to agents. Provides:
- Tool discovery and listing
- JSON schema validation for tool inputs
- Approval gate enforcement
- Tool execution with mocking support
- MCP (Model Context Protocol) tool integration
"""

from __future__ import annotations

import json
from typing import Any, Callable

import structlog
from jsonschema import validate, ValidationError as JsonSchemaValidationError
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.blacklight.features.agents.spec_schema import ToolSpec, TransportType
from src.blacklight.features.agents.tools.mock_tools import MOCK_TOOLS
from src.blacklight.features.agents.tools.exceptions import ApprovalRequiredError
from src.blacklight.features.agents.tools.mcp_adapter import (
    MCPToolAdapter,
    convert_mcp_tool_to_spec,
    create_mcp_tool_wrapper,
)

logger = structlog.get_logger(__name__)


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found in the registry"""

    pass


class ToolValidationError(Exception):
    """Raised when tool input fails schema validation"""

    pass


class ToolRegistry:
    """
    Central registry for agent tools.

    Manages tool discovery, validation, and execution. Supports:
    - Built-in tools and mock implementations
    - MCP (Model Context Protocol) tools from external servers
    - Dynamic tool loading and caching
    """

    def __init__(self, mcp_adapter: MCPToolAdapter | None = None):
        """
        Initialize the registry with built-in mock tools.

        Args:
            mcp_adapter: Optional MCP tool adapter for audit logging
        """
        self._tools: dict[str, dict[str, Any]] = {}
        self._mcp_tools: dict[str, list[ToolSpec]] = {}  # server_name -> tool specs
        self._mcp_base_tools: dict[str, list[BaseTool]] = {}  # server_name -> BaseTool instances
        self._mcp_adapter = mcp_adapter or MCPToolAdapter()
        self._load_mock_tools()

    def _load_mock_tools(self):
        """Load built-in mock tools into the registry"""
        for tool_name, tool_data in MOCK_TOOLS.items():
            self._tools[tool_name] = tool_data

    def list(self) -> list[ToolSpec]:
        """
        List all available tools (local + MCP).

        Returns:
            List of ToolSpec models for all registered tools
        """
        specs = []

        # Add local tools
        for tool_name, tool_data in self._tools.items():
            specs.append(
                ToolSpec(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    requires_approval=tool_data["requires_approval"],
                    input_schema=tool_data["input_schema"],
                    transport=TransportType(tool_data["transport"]),
                    config=tool_data.get("config"),
                    implementation_hint=tool_data.get("implementation_hint", ""),
                )
            )

        # Add MCP tools
        for server_name, mcp_tools in self._mcp_tools.items():
            specs.extend(mcp_tools)

        return specs

    def get(self, name: str) -> ToolSpec:
        """
        Get tool specification by name (searches local + MCP tools).

        Args:
            name: Tool name

        Returns:
            ToolSpec for the tool

        Raises:
            ToolNotFoundError: If tool is not found
        """
        # Check local tools first
        if name in self._tools:
            tool_data = self._tools[name]
            return ToolSpec(
                name=tool_data["name"],
                description=tool_data["description"],
                requires_approval=tool_data["requires_approval"],
                input_schema=tool_data["input_schema"],
                transport=TransportType(tool_data["transport"]),
                config=tool_data.get("config"),
                implementation_hint=tool_data.get("implementation_hint", ""),
            )

        # Check MCP tools
        for server_name, mcp_tools in self._mcp_tools.items():
            for tool in mcp_tools:
                if tool.name == name:
                    return tool

        raise ToolNotFoundError(f"Tool '{name}' not found in registry")

    def make_callable(
        self,
        name: str,
        approval_granted: bool = False,
        mock_response: dict[str, Any] | None = None,
    ) -> Callable:
        """
        Create a callable wrapper for a tool that enforces validation and approval.

        Args:
            name: Tool name
            approval_granted: Whether approval has been granted for this execution
            mock_response: Optional mock response (for testing)

        Returns:
            Callable function that executes the tool

        Raises:
            ToolNotFoundError: If tool is not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")

        tool_data = self._tools[name]
        tool_impl = tool_data["implementation"]
        schema = tool_data["input_schema"]
        requires_approval = tool_data["requires_approval"]

        def tool_wrapper(**kwargs) -> dict[str, Any]:
            """Wrapper that validates input and enforces approval"""

            # Validate input against JSON schema
            try:
                validate(instance=kwargs, schema=schema)
            except JsonSchemaValidationError as e:
                raise ToolValidationError(
                    f"Tool '{name}' input validation failed: {e.message}"
                )

            # Check approval requirement
            if requires_approval and not approval_granted:
                raise ApprovalRequiredError(name, kwargs)

            # Return mock response if provided (for testing)
            if mock_response is not None:
                return mock_response

            # Execute real tool implementation
            return tool_impl(**kwargs)

        return tool_wrapper

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        implementation: Callable,
        requires_approval: bool = False,
        transport: str = "local",
        config: dict[str, Any] | None = None,
    ):
        """
        Register a new tool in the registry.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool input
            implementation: Callable that implements the tool
            requires_approval: Whether tool requires approval
            transport: Transport type (local, http, mcp)
            config: Optional configuration dictionary
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "requires_approval": requires_approval,
            "input_schema": input_schema,
            "transport": transport,
            "config": config,
            "implementation": implementation,
        }

    def get_catalog_text(self) -> str:
        """
        Get a formatted text catalog of all tools for LLM prompts.

        Returns:
            Formatted string listing all tools with their schemas (local + MCP)
        """
        lines = ["AVAILABLE TOOLS:", ""]

        # Local tools
        if self._tools:
            lines.append("## Local Tools")
            lines.append("")
            for tool_name, tool_data in self._tools.items():
                lines.append(f"- **{tool_name}**")
                lines.append(f"  Description: {tool_data['description']}")
                lines.append(f"  Requires Approval: {tool_data['requires_approval']}")
                lines.append(f"  Transport: {tool_data['transport']}")
                lines.append(f"  Input Schema: {json.dumps(tool_data['input_schema'], indent=2)}")
                lines.append("")

        # MCP tools (grouped by server)
        if self._mcp_tools:
            lines.append("## MCP Tools")
            lines.append("")
            for server_name, tools in self._mcp_tools.items():
                lines.append(f"### MCP Server: {server_name}")
                lines.append(f"    Available tools: {len(tools)}")
                lines.append("")
                for tool in tools:
                    lines.append(f"    - **{tool.name}** (from {server_name})")
                    lines.append(f"      Description: {tool.description}")
                    lines.append(f"      Requires Approval: {tool.requires_approval}")
                    lines.append(f"      Input Schema: {json.dumps(tool.input_schema, indent=2)}")
                    lines.append("")

        return "\n".join(lines)

    def register_mcp_server(
        self,
        server_name: str,
        tools: list[BaseTool],
        requires_approval: bool = False,
    ):
        """
        Register MCP tools from a server.

        Args:
            server_name: Name of the MCP server
            tools: List of LangChain BaseTool instances
            requires_approval: Whether tools require user approval
        """
        # Convert MCP tools to ToolSpecs
        tool_specs = self._mcp_adapter.convert_tools(tools, server_name, requires_approval)

        # Store tool specs and original BaseTool instances
        self._mcp_tools[server_name] = tool_specs
        self._mcp_base_tools[server_name] = tools

        logger.info(
            "mcp_server_registered",
            server=server_name,
            tool_count=len(tools),
            requires_approval=requires_approval,
        )

    def get_mcp_tools(self, server_name: str | None = None) -> list[ToolSpec]:
        """
        Get MCP tools from a specific server or all servers.

        Args:
            server_name: Optional server name to filter by

        Returns:
            List of ToolSpec instances
        """
        if server_name:
            return self._mcp_tools.get(server_name, [])

        # Return all MCP tools from all servers
        all_tools = []
        for tools in self._mcp_tools.values():
            all_tools.extend(tools)
        return all_tools

    def get_mcp_base_tool(self, server_name: str, tool_name: str) -> BaseTool | None:
        """
        Get the original LangChain BaseTool instance for execution.

        Args:
            server_name: MCP server name
            tool_name: Tool name

        Returns:
            BaseTool instance or None if not found
        """
        if server_name not in self._mcp_base_tools:
            return None

        for tool in self._mcp_base_tools[server_name]:
            if tool.name == tool_name:
                return tool

        return None

    def list_mcp_servers(self) -> list[str]:
        """
        List all registered MCP server names.

        Returns:
            List of server names
        """
        return list(self._mcp_tools.keys())

    def unregister_mcp_server(self, server_name: str):
        """
        Remove MCP server and its tools from registry.

        Args:
            server_name: Name of the server to remove
        """
        self._mcp_tools.pop(server_name, None)
        self._mcp_base_tools.pop(server_name, None)
        logger.info("mcp_server_unregistered", server=server_name)


# Global registry instance
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    return _registry
