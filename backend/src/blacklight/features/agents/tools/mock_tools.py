"""
Mock Tool Implementations

These are stub tools for testing the agent build system.
In production, these would be replaced with real implementations.
"""

from typing import Any


def search_kb(query: str) -> dict[str, Any]:
    """
    Mock knowledge base search tool.

    Args:
        query: Search query string

    Returns:
        Mock search results
    """
    return {
        "results": [
            {
                "title": "Mock KB Article 1",
                "url": "https://kb.example.com/article-1",
                "snippet": f"This is a mock result for query: {query}",
                "relevance": 0.95,
            },
            {
                "title": "Mock KB Article 2",
                "url": "https://kb.example.com/article-2",
                "snippet": f"Another mock result for: {query}",
                "relevance": 0.87,
            },
        ],
        "total": 2,
        "query": query,
    }


def create_ticket(summary: str, body: str, priority: str = "normal") -> dict[str, Any]:
    """
    Mock support ticket creation tool.

    Args:
        summary: Ticket summary/title
        body: Ticket description
        priority: Ticket priority (low, normal, high, urgent)

    Returns:
        Mock ticket creation result
    """
    import uuid
    from datetime import datetime

    ticket_id = f"MOCK-{str(uuid.uuid4())[:8].upper()}"

    return {
        "ticket_id": ticket_id,
        "summary": summary,
        "body": body,
        "priority": priority,
        "status": "created",
        "created_at": datetime.utcnow().isoformat(),
        "url": f"https://tickets.example.com/{ticket_id}",
    }


def add(first_number: float, second_number: float) -> dict[str, Any]:
    """
    Add two numbers together.

    Args:
        first_number: First number
        second_number: Second number

    Returns:
        Dict with the result
    """
    return {"result": first_number + second_number}


def multiply(first_number: float, second_number: float) -> dict[str, Any]:
    """
    Multiply two numbers.

    Args:
        first_number: First number
        second_number: Second number

    Returns:
        Dict with the result
    """
    return {"result": first_number * second_number}


def divide(first_number: float, second_number: float) -> dict[str, Any]:
    """
    Divide first number by second number.

    Args:
        first_number: Numerator
        second_number: Denominator

    Returns:
        Dict with the result

    Raises:
        ValueError: If second_number is zero
    """
    if second_number == 0:
        raise ValueError("Cannot divide by zero")
    return {"result": first_number / second_number}


def send_email(to: str, subject: str, body: str, from_email: str = "agent@example.com") -> dict[str, Any]:
    """
    Mock email sending tool.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        from_email: Sender email address

    Returns:
        Mock email send result
    """
    import uuid
    from datetime import datetime

    message_id = str(uuid.uuid4())

    return {
        "sent": True,
        "message_id": message_id,
        "to": to,
        "from": from_email,
        "subject": subject,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Tool metadata registry
MOCK_TOOLS = {
    "add": {
        "name": "add",
        "description": "Add two numbers together",
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "first_number": {
                    "type": "number",
                    "description": "First number"
                },
                "second_number": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["first_number", "second_number"]
        },
        "transport": "local",
        "implementation": add,
    },
    "multiply": {
        "name": "multiply",
        "description": "Multiply two numbers",
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "first_number": {
                    "type": "number",
                    "description": "First number"
                },
                "second_number": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["first_number", "second_number"]
        },
        "transport": "local",
        "implementation": multiply,
    },
    "divide": {
        "name": "divide",
        "description": "Divide first number by second number",
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "first_number": {
                    "type": "number",
                    "description": "Numerator"
                },
                "second_number": {
                    "type": "number",
                    "description": "Denominator (cannot be zero)"
                }
            },
            "required": ["first_number", "second_number"]
        },
        "transport": "local",
        "implementation": divide,
    },
    "search_kb": {
        "name": "search_kb",
        "description": "Search internal knowledge base for articles and documentation",
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        },
        "transport": "local",
        "implementation": search_kb,
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Create a support ticket in the ticketing system",
        "requires_approval": True,
        "input_schema": {
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
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Ticket priority",
                    "default": "normal"
                }
            },
            "required": ["summary", "body"]
        },
        "transport": "local",
        "implementation": create_ticket,
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email message",
        "requires_approval": False,
        "input_schema": {
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
            "required": ["to", "subject", "body"]
        },
        "transport": "local",
        "implementation": send_email,
    },
}
