"""
Tool Exceptions

Custom exceptions for tool execution and approval workflows.
"""

from typing import Any


class ApprovalRequiredError(Exception):
    """
    Exception raised when a tool requires approval before execution.

    This exception signals that the tool cannot proceed without explicit
    user or admin approval, typically for sensitive operations.
    """

    def __init__(self, tool_name: str, parameters: dict[str, Any]):
        self.tool_name = tool_name
        self.parameters = parameters
        super().__init__(
            f"Tool '{tool_name}' requires approval before execution. "
            f"Parameters: {parameters}"
        )


class ToolExecutionError(Exception):
    """
    Exception raised when tool execution fails.

    This wraps underlying errors from tool implementations and provides
    consistent error handling across different tool types.
    """

    def __init__(self, tool_name: str, error: Exception):
        self.tool_name = tool_name
        self.original_error = error
        super().__init__(f"Tool '{tool_name}' execution failed: {str(error)}")
