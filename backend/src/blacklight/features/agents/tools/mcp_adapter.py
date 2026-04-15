"""
MCP Tool Adapter

Adapts MCP (Model Context Protocol) tools to Blacklight's tool format.
Provides execution wrappers with audit logging, approval gates, and metrics tracking.

Key features:
- Convert LangChain BaseTool to Blacklight ToolSpec
- Wrap tool execution with audit logging
- Enforce approval gates for sensitive tools
- Track execution time and success/failure metrics
- Support for async tool execution
"""

import time
from typing import Any, Callable

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.blacklight.features.agents.spec_schema import ToolSpec, TransportType
from src.blacklight.features.agents.tools.exceptions import ApprovalRequiredError

logger = structlog.get_logger(__name__)


class MCPToolMetadata(BaseModel):
    """Metadata for MCP tools"""

    server_name: str
    requires_approval: bool = False
    original_tool: BaseTool


def convert_mcp_tool_to_spec(
    tool: BaseTool, server_name: str, requires_approval: bool = False
) -> ToolSpec:
    """
    Convert a LangChain BaseTool from MCP to Blacklight ToolSpec.

    Args:
        tool: LangChain BaseTool instance
        server_name: Name of the MCP server providing this tool
        requires_approval: Whether tool requires user approval

    Returns:
        ToolSpec compatible with Blacklight's tool system
    """
    # Extract input schema from LangChain tool
    input_schema: dict[str, Any] = {}
    if hasattr(tool, "args_schema") and tool.args_schema:
        # Convert Pydantic model to JSON schema
        if hasattr(tool.args_schema, "schema"):
            input_schema = tool.args_schema.schema()  # type: ignore[attr-defined]
        else:
            input_schema = {}
    elif hasattr(tool, "args") and tool.args:
        # Fallback to args dict
        input_schema = {
            "type": "object",
            "properties": {k: {"type": "string"} for k in tool.args.keys()},
            "required": list(tool.args.keys()),
        }
    else:
        # No schema available, accept any JSON object
        input_schema = {"type": "object", "properties": {}, "additionalProperties": True}  # type: ignore[dict-item]

    return ToolSpec(
        name=tool.name,
        description=tool.description or f"Tool from MCP server: {server_name}",
        requires_approval=requires_approval,
        input_schema=input_schema,
        transport=TransportType.MCP,
        config={"server": server_name},
        implementation_hint="",  # MCP tools don't need implementation hints
    )


def create_mcp_tool_wrapper(
    tool: BaseTool,
    server_name: str,
    requires_approval: bool = False,
    audit_callback: Callable | None = None,
) -> Callable:
    """
    Create an execution wrapper for an MCP tool.

    Wraps the tool with:
    - Input validation
    - Approval gate enforcement
    - Execution time tracking
    - Audit logging
    - Error handling

    Args:
        tool: LangChain BaseTool instance
        server_name: Name of the MCP server
        requires_approval: Whether tool requires user approval
        audit_callback: Optional async callback for audit logging
            Signature: async def callback(server_name, tool_name, params, result, status, error, time_ms)

    Returns:
        Callable wrapper function
    """

    async def wrapper(approval_granted: bool = False, **kwargs) -> dict[str, Any]:
        """
        Execute MCP tool with tracking and logging.

        Args:
            approval_granted: Whether user has granted approval
            **kwargs: Tool parameters

        Returns:
            Dict with 'result' and optional 'error' keys

        Raises:
            ApprovalRequiredError: If approval required but not granted
            ToolValidationError: If parameters are invalid
        """
        start_time = time.time()
        result = None
        error_msg = None
        status = "success"

        try:
            # Check approval requirement
            if requires_approval and not approval_granted:
                raise ApprovalRequiredError(tool.name, kwargs)

            # Validate input (LangChain tool will validate via args_schema)
            logger.info(
                "mcp_tool_executing",
                server=server_name,
                tool=tool.name,
                params=kwargs,
            )

            # Execute tool (async if supported)
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(kwargs)
            else:
                # Sync tool - run in executor to avoid blocking
                import asyncio

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool.invoke(kwargs))

            logger.info(
                "mcp_tool_success",
                server=server_name,
                tool=tool.name,
                result_preview=str(result)[:200] if result else None,
            )

            return {"result": result}

        except ApprovalRequiredError:
            status = "approval_required"
            error_msg = f"Tool '{tool.name}' requires user approval"
            logger.warning(
                "mcp_tool_approval_required",
                server=server_name,
                tool=tool.name,
            )
            raise

        except Exception as e:
            status = "error"
            error_msg = str(e)
            logger.error(
                "mcp_tool_error",
                server=server_name,
                tool=tool.name,
                error=error_msg,
                exc_info=True,
            )
            return {"error": error_msg}

        finally:
            # Track execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log to audit trail
            if audit_callback:
                try:
                    await audit_callback(
                        server_name=server_name,
                        tool_name=tool.name,
                        parameters=kwargs,
                        result=result if status == "success" else None,
                        status=status,
                        error_message=error_msg,
                        execution_time_ms=execution_time_ms,
                    )
                except Exception as audit_error:
                    logger.error(
                        "mcp_audit_logging_failed",
                        server=server_name,
                        tool=tool.name,
                        error=str(audit_error),
                    )

    return wrapper


def convert_mcp_tools_to_specs(
    tools: list[BaseTool],
    server_name: str,
    requires_approval: bool = False,
) -> list[ToolSpec]:
    """
    Convert multiple MCP tools to ToolSpecs.

    Args:
        tools: List of LangChain BaseTool instances
        server_name: Name of the MCP server
        requires_approval: Whether tools require user approval

    Returns:
        List of ToolSpec instances
    """
    specs = []
    for tool in tools:
        try:
            spec = convert_mcp_tool_to_spec(tool, server_name, requires_approval)
            specs.append(spec)
        except Exception as e:
            logger.error(
                "mcp_tool_conversion_failed",
                server=server_name,
                tool=tool.name if hasattr(tool, "name") else "unknown",
                error=str(e),
            )
            # Continue processing other tools
            continue

    logger.info(
        "mcp_tools_converted",
        server=server_name,
        total_tools=len(tools),
        converted=len(specs),
    )

    return specs


async def get_mcp_tool_catalog_text(
    mcp_tools_by_server: dict[str, list[ToolSpec]],
) -> str:
    """
    Generate formatted text catalog of MCP tools for LLM prompts.

    Args:
        mcp_tools_by_server: Dict mapping server names to tool specs

    Returns:
        Formatted string listing all MCP tools grouped by server
    """
    if not mcp_tools_by_server:
        return "No MCP tools currently available."

    lines = ["AVAILABLE MCP TOOLS:", ""]

    for server_name, tools in mcp_tools_by_server.items():
        lines.append(f"## MCP Server: {server_name}")
        lines.append(f"   Tools: {len(tools)}")
        lines.append("")

        for tool in tools:
            lines.append(f"   - **{tool.name}** (MCP: {server_name})")
            lines.append(f"     Description: {tool.description}")
            lines.append(f"     Requires Approval: {tool.requires_approval}")
            lines.append(f"     Input Schema: {tool.input_schema}")
            lines.append("")

        lines.append("")

    return "\n".join(lines)


class MCPToolAdapter:
    """
    High-level adapter for working with MCP tools.

    Provides convenience methods for:
    - Converting MCP tools to Blacklight format
    - Creating execution wrappers with audit logging
    - Generating tool catalogs
    """

    def __init__(self, audit_callback: Callable | None = None):
        """
        Initialize MCP tool adapter.

        Args:
            audit_callback: Optional async callback for audit logging
        """
        self.audit_callback = audit_callback

    def convert_tools(
        self,
        tools: list[BaseTool],
        server_name: str,
        requires_approval: bool = False,
    ) -> list[ToolSpec]:
        """Convert MCP tools to ToolSpecs"""
        return convert_mcp_tools_to_specs(tools, server_name, requires_approval)

    def create_wrapper(
        self,
        tool: BaseTool,
        server_name: str,
        requires_approval: bool = False,
    ) -> Callable:
        """Create execution wrapper for MCP tool"""
        return create_mcp_tool_wrapper(
            tool,
            server_name,
            requires_approval,
            self.audit_callback,
        )

    async def get_catalog_text(
        self, mcp_tools_by_server: dict[str, list[ToolSpec]]
    ) -> str:
        """Generate text catalog of MCP tools"""
        return await get_mcp_tool_catalog_text(mcp_tools_by_server)
