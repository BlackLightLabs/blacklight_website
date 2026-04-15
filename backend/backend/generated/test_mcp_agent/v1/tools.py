"""
Tool registry for WebTesterAgent

Auto-generated tool wrappers with validation and approval gates.
DO NOT EDIT MANUALLY - changes will be overwritten on rebuild.
"""

from typing import Any, Callable
from jsonschema import validate, ValidationError

# MCP imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import BaseTool

# Global MCP client and tools
_mcp_client: MultiServerMCPClient | None = None
_mcp_tools: dict[str, BaseTool] = {}  # tool_name -> BaseTool


# Tool implementations (will be mocked during tests)
def tool_browser_navigate(**kwargs) -> dict[str, Any]:
    """
    Navigate to URL


    Transport: TransportType.MCP
    """
    # Input validation
    schema = {
  "type": "object",
  "properties": {
    "url": {
      "type": "string"
    }
  }
}

    try:
        validate(instance=kwargs, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Tool 'browser_navigate' input validation failed: {e.message}")


    # Call the actual tool implementation
    # During tests, this will be mocked
    if hasattr(tool_browser_navigate, '_mock_response'):
        return tool_browser_navigate._mock_response

    # In real execution, this would call the actual tool via transport
    # MCP tool execution
    if "browser_navigate" in _mcp_tools:
        mcp_tool = _mcp_tools["browser_navigate"]
        # Call MCP tool (async if supported)
        import asyncio
        if hasattr(mcp_tool, 'ainvoke'):
            result = asyncio.run(mcp_tool.ainvoke(kwargs))
        else:
            result = mcp_tool.invoke(kwargs)
        return {"result": result} if not isinstance(result, dict) else result
    else:
        raise RuntimeError(f"MCP tool 'browser_navigate' not initialized")

def tool_browser_screenshot(**kwargs) -> dict[str, Any]:
    """
    Capture screenshot


    Transport: TransportType.MCP
    """
    # Input validation
    schema = {
  "type": "object",
  "properties": {}
}

    try:
        validate(instance=kwargs, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Tool 'browser_screenshot' input validation failed: {e.message}")


    # Call the actual tool implementation
    # During tests, this will be mocked
    if hasattr(tool_browser_screenshot, '_mock_response'):
        return tool_browser_screenshot._mock_response

    # In real execution, this would call the actual tool via transport
    # MCP tool execution
    if "browser_screenshot" in _mcp_tools:
        mcp_tool = _mcp_tools["browser_screenshot"]
        # Call MCP tool (async if supported)
        import asyncio
        if hasattr(mcp_tool, 'ainvoke'):
            result = asyncio.run(mcp_tool.ainvoke(kwargs))
        else:
            result = mcp_tool.invoke(kwargs)
        return {"result": result} if not isinstance(result, dict) else result
    else:
        raise RuntimeError(f"MCP tool 'browser_screenshot' not initialized")


# Tool registry dictionary
TOOLS: dict[str, Callable] = {
    "browser_navigate": tool_browser_navigate,
    "browser_screenshot": tool_browser_screenshot,
}


def set_mock_response(tool_name: str, response: dict[str, Any]):
    """Set a mock response for a tool (used in testing)"""
    if tool_name in TOOLS:
        TOOLS[tool_name]._mock_response = response


def grant_approval(tool_name: str):
    """Grant approval for a tool execution (used in testing)"""
    if tool_name in TOOLS:
        TOOLS[tool_name]._approval_granted = True


def clear_mocks():
    """Clear all mocks and approvals"""
    for tool_fn in TOOLS.values():
        if hasattr(tool_fn, '_mock_response'):
            delattr(tool_fn, '_mock_response')
        if hasattr(tool_fn, '_approval_granted'):
            delattr(tool_fn, '_approval_granted')


async def initialize_mcp_tools():
    """
    Initialize MCP client and load tools from configured servers.

    This function must be called before using the agent to load MCP tools.
    """
    global _mcp_client, _mcp_tools

    # Load MCP server configurations from database
    from src.blacklight.features.agents.mcp_repository import MCPServerRepository
    from src.blacklight.common.database import async_session_maker

    async with async_session_maker() as db:
        mcp_repo = MCPServerRepository(db)

        # Build server config for MCP client
        server_configs = {}
        # Load playwright server configuration
        db_server = await mcp_repo.get_by_name("playwright")
        if db_server and db_server.is_enabled:
            server_config = {
                "transport": db_server.transport.value.lower(),
                **db_server.connection_config
            }
            server_configs["playwright"] = server_config

    if not server_configs:
        # No MCP servers configured
        return

    # Initialize MCP client
    _mcp_client = MultiServerMCPClient(server_configs)

    # Load tools from each server
    try:
        async with _mcp_client.session("playwright") as session:
            tools = await load_mcp_tools(session)
            for tool in tools:
                _mcp_tools[tool.name] = tool
    except Exception as e:
        # Log error but don't fail initialization
        print(f"Warning: Failed to load tools from playwright: {e}")


async def shutdown_mcp_tools():
    """Cleanup MCP client resources"""
    global _mcp_client, _mcp_tools
    _mcp_client = None
    _mcp_tools = {}
