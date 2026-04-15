"""
Tool registry for Simple Calculator

Auto-generated tool wrappers with validation and approval gates.
DO NOT EDIT MANUALLY - changes will be overwritten on rebuild.
"""

from typing import Any, Callable
from jsonschema import validate, ValidationError



# Tool implementations (will be mocked during tests)

# Tool registry dictionary
TOOLS: dict[str, Callable] = {
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
    """No-op when no MCP servers configured"""
    pass


async def shutdown_mcp_tools():
    """No-op when no MCP servers configured"""
    pass
