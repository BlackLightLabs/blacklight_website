"""
Tool registry for Website Test Agent

Auto-generated tool wrappers with validation and approval gates.
DO NOT EDIT MANUALLY - changes will be overwritten on rebuild.
"""

from typing import Any, Callable
from jsonschema import validate, ValidationError



# Tool implementations (will be mocked during tests)
def tool_search_kb(**kwargs) -> dict[str, Any]:
    """
    Search internal knowledge base for articles and documentation


    Transport: TransportType.LOCAL
    """
    # Input validation
    schema = {
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query"
    }
  },
  "required": [
    "query"
  ]
}

    try:
        validate(instance=kwargs, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Tool 'search_kb' input validation failed: {e.message}")


    # Call the actual tool implementation
    # During tests, this will be mocked
    if hasattr(tool_search_kb, '_mock_response'):
        return tool_search_kb._mock_response

    # In real execution, this would call the actual tool via transport
    # Local tool execution
    from src.blacklight.features.agents.tools.mock_tools import search_kb
    return search_kb(**kwargs)

def tool_create_ticket(**kwargs) -> dict[str, Any]:
    """
    Create a support ticket in the ticketing system

    ⚠️ This tool requires approval before execution

    Transport: TransportType.LOCAL
    """
    # Input validation
    schema = {
  "type": "object",
  "properties": {
    "summary": {
      "type": "string",
      "description": "Ticket summary/title"
    },
    "body": {
      "type": "string",
      "description": "Ticket description"
    },
    "priority": {
      "type": "string",
      "enum": [
        "low",
        "normal",
        "high",
        "urgent"
      ],
      "description": "Ticket priority",
      "default": "normal"
    }
  },
  "required": [
    "summary",
    "body"
  ]
}

    try:
        validate(instance=kwargs, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Tool 'create_ticket' input validation failed: {e.message}")

    # Approval check (will be enforced at runtime)
    if not getattr(tool_create_ticket, '_approval_granted', False):
        raise RuntimeError("Tool 'create_ticket' requires approval")

    # Call the actual tool implementation
    # During tests, this will be mocked
    if hasattr(tool_create_ticket, '_mock_response'):
        return tool_create_ticket._mock_response

    # In real execution, this would call the actual tool via transport
    # Local tool execution
    from src.blacklight.features.agents.tools.mock_tools import create_ticket
    return create_ticket(**kwargs)

def tool_send_email(**kwargs) -> dict[str, Any]:
    """
    Send an email message


    Transport: TransportType.LOCAL
    """
    # Input validation
    schema = {
  "type": "object",
  "properties": {
    "to": {
      "type": "string",
      "description": "Recipient email address",
      "format": "email"
    },
    "subject": {
      "type": "string",
      "description": "Email subject"
    },
    "body": {
      "type": "string",
      "description": "Email body"
    },
    "from_email": {
      "type": "string",
      "description": "Sender email address",
      "format": "email",
      "default": "agent@example.com"
    }
  },
  "required": [
    "to",
    "subject",
    "body"
  ]
}

    try:
        validate(instance=kwargs, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Tool 'send_email' input validation failed: {e.message}")


    # Call the actual tool implementation
    # During tests, this will be mocked
    if hasattr(tool_send_email, '_mock_response'):
        return tool_send_email._mock_response

    # In real execution, this would call the actual tool via transport
    # Local tool execution
    from src.blacklight.features.agents.tools.mock_tools import send_email
    return send_email(**kwargs)


# Tool registry dictionary
TOOLS: dict[str, Callable] = {
    "search_kb": tool_search_kb,
    "create_ticket": tool_create_ticket,
    "send_email": tool_send_email,
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
