"""
Agent Specification Schema

Defines the strict schema for agent specifications that are compiled into
LangGraph workflows. This schema ensures agents are well-formed, testable,
and safe before code generation.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class NodeType(str, Enum):
    """Types of nodes that can be created in an agent graph"""

    LLM = "llm"
    TOOL = "tool"
    ROUTER = "router"
    PYTHON = "python"


class AssertionType(str, Enum):
    """Types of assertions for test validation"""

    TOOL_CALLED = "tool_called"
    STATE_CONTAINS = "state_contains"
    VERIFIER_PASS = "verifier_pass"
    NO_ERRORS = "no_errors"
    BUDGET_RESPECTED = "budget_respected"


class TransportType(str, Enum):
    """Tool transport mechanisms"""

    LOCAL = "local"
    HTTP = "http"
    MCP = "mcp"


class StateField(BaseModel):
    """Definition of a field in the agent's state"""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Type annotation (e.g., 'str', 'dict', 'list[str]')")
    description: str | None = Field(None, description="Field description")


class StopCondition(BaseModel):
    """Condition to stop node execution"""

    field: str = Field(..., description="State field to check")
    includes: str | None = Field(None, description="Value must include this string")
    equals: Any | None = Field(None, description="Value must equal this")


class NodeSpec(BaseModel):
    """Specification for a single node in the agent graph"""

    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Node type")
    input: list[str] = Field(
        default_factory=list, description="State fields this node reads"
    )
    output: list[str] = Field(
        default_factory=list, description="State fields this node writes"
    )
    prompt: str | None = Field(None, description="Prompt template for LLM nodes")
    tool: str | None = Field(None, description="Tool name for tool nodes")
    tools_allowed: list[str] | None = Field(
        None, description="Tools the LLM can call (for LLM nodes)"
    )
    input_mapping: dict[str, str] | None = Field(
        None, description="Map state fields to tool parameters (for tool nodes)"
    )
    stop_conditions: list[StopCondition] | None = Field(
        None, description="Conditions to stop execution"
    )

    @model_validator(mode="after")
    def validate_node_fields(self):
        """Validate node has required fields based on type"""
        if self.type == NodeType.LLM and not self.prompt:
            raise ValueError(f"LLM node '{self.id}' must have a prompt")
        if self.type == NodeType.TOOL and not self.tool:
            raise ValueError(f"Tool node '{self.id}' must specify a tool")
        return self


class EdgeSpec(BaseModel):
    """Specification for an edge in the agent graph"""

    from_node: str = Field(..., alias="from", description="Source node ID")
    to_node: str = Field(..., alias="to", description="Target node ID")
    condition: str | None = Field(None, description="Optional condition for edge")


class ToolSpec(BaseModel):
    """Specification for a tool that can be used by the agent"""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="What the tool does")
    requires_approval: bool = Field(
        False, description="Whether tool needs user approval"
    )
    input_schema: dict[str, Any] = Field(..., description="JSON Schema for tool input")
    implementation_hint: str | None = Field(
        None, description="Hint for code generation (e.g., 'wrap internal search API')"
    )
    transport: TransportType = Field(
        TransportType.LOCAL, description="How the tool is invoked"
    )
    config: dict[str, Any] | None = Field(
        None, description="Tool-specific configuration (endpoints, auth, etc.)"
    )


class TestAssertion(BaseModel):
    """Assertion to validate during a test run"""

    type: AssertionType = Field(..., description="Type of assertion")
    name: str | None = Field(None, description="Tool/verifier name (for tool_called, verifier_pass)")
    path: str | None = Field(None, description="JSONPath to check (for state_contains)")
    value: Any | None = Field(None, description="Expected value (for state_contains)")


class TestCase(BaseModel):
    """Test case specification"""

    name: str = Field(..., description="Test case name")
    input: dict[str, Any] = Field(..., description="Initial state for the test")
    assertions: list[TestAssertion] = Field(
        ..., description="Assertions to validate"
    )
    mocks: dict[str, Any] | None = Field(
        None, description="Mock responses for tools (tool_name -> response)"
    )


class VerifierSpec(BaseModel):
    """Runtime verification specification"""

    type: Literal["tool_call"] = Field(..., description="Type of verifier")
    tool: str = Field(..., description="Tool to call for verification")
    expect: str = Field(..., description="Expected condition (Python expression)")


class PolicySpec(BaseModel):
    """Safety and access control policies"""

    deny_patterns: list[str] | None = Field(
        None, description="Regex patterns to block in outputs"
    )
    grants: list[dict[str, Any]] | None = Field(
        None, description="Permissions granted (e.g., {'tool': 'create_ticket', 'scope': 'credits<=500'})"
    )


class RuntimeConfig(BaseModel):
    """Runtime execution configuration"""

    max_steps: int = Field(12, description="Maximum graph execution steps")
    budget_usd: float = Field(2.00, description="Maximum cost per execution")
    timeout_seconds: int = Field(30, description="Maximum execution time")


class MCPServerSpec(BaseModel):
    """
    MCP (Model Context Protocol) server configuration for an agent.

    Agents can connect to external MCP servers to access additional tools
    dynamically at runtime (e.g., browser automation, APIs, databases).
    """

    name: str = Field(..., description="MCP server name (must match registered server)")
    enabled: bool = Field(True, description="Whether to load tools from this server")
    config_overrides: dict[str, Any] | None = Field(
        None, description="Agent-specific server configuration overrides"
    )


class AgentSpec(BaseModel):
    """Complete agent specification for compilation and testing"""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="What the agent does")
    model: str = Field("qwen/qwen3-coder-30b", description="LLM model to use")
    state: list[StateField] = Field(..., description="State schema fields")
    nodes: list[NodeSpec] = Field(..., description="Graph nodes")
    edges: list[EdgeSpec] = Field(..., description="Graph edges")
    tools: list[ToolSpec] = Field(default_factory=list, description="Available tools")
    mcp_servers: list[MCPServerSpec] = Field(
        default_factory=list, description="MCP servers to connect to at runtime"
    )
    tests: list[TestCase] = Field(..., description="Test cases (at least 1 required)")
    verifiers: list[VerifierSpec] | None = Field(
        None, description="Runtime verifiers"
    )
    policies: PolicySpec | None = Field(None, description="Safety policies")
    runtime: RuntimeConfig = Field(
        default_factory=RuntimeConfig,  # type: ignore[arg-type]
        description="Runtime configuration",
    )

    @field_validator("tests")
    @classmethod
    def validate_has_tests(cls, v):
        """Ensure at least one test case"""
        if not v or len(v) == 0:
            raise ValueError("Agent spec must have at least 1 test case")
        return v

    @model_validator(mode="after")
    def validate_graph_structure(self):
        """Validate graph is well-formed (nodes, edges, tools all match)"""
        node_ids = {node.id for node in self.nodes}
        tool_names = {tool.name for tool in self.tools}

        # Validate edges reference existing nodes
        for edge in self.edges:
            if edge.from_node not in node_ids and edge.from_node != "START":
                raise ValueError(f"Edge references unknown node: {edge.from_node}")
            if edge.to_node not in node_ids and edge.to_node != "END":
                raise ValueError(f"Edge references unknown node: {edge.to_node}")

        # Validate tool nodes reference existing tools
        for node in self.nodes:
            if node.type == NodeType.TOOL:
                if node.tool and node.tool not in tool_names:
                    raise ValueError(
                        f"Node '{node.id}' references unknown tool: {node.tool}"
                    )
            if node.tools_allowed:
                for tool in node.tools_allowed:
                    if tool not in tool_names:
                        raise ValueError(
                            f"Node '{node.id}' allows unknown tool: {tool}"
                        )

        # Validate state fields referenced in nodes exist
        state_field_names = {field.name for field in self.state}
        for node in self.nodes:
            for field in node.input + node.output:
                if field not in state_field_names:
                    raise ValueError(
                        f"Node '{node.id}' references unknown state field: {field}"
                    )

        return self


# Example specifications for testing and documentation

EXAMPLE_SUPPORT_AGENT = {
    "name": "Support Ticket Creator",
    "description": "Searches knowledge base and creates support tickets for user issues",
    "model": "qwen/qwen3-coder-30b",
    "state": [
        {"name": "user_input", "type": "str", "description": "User's problem description"},
        {"name": "kb_results", "type": "list[dict]", "description": "Search results from KB"},
        {"name": "ticket_id", "type": "str | None", "description": "Created ticket ID"},
        {"name": "result", "type": "str", "description": "Final response to user"},
    ],
    "nodes": [
        {
            "id": "search_kb",
            "type": "tool",
            "tool": "search_kb",
            "input": ["user_input"],
            "output": ["kb_results"],
            "input_mapping": {"query": "user_input"},
        },
        {
            "id": "create_ticket",
            "type": "tool",
            "tool": "create_ticket",
            "input": ["user_input", "kb_results"],
            "output": ["ticket_id"],
            "input_mapping": {
                "summary": "user_input",
                "body": "kb_results",
            },
        },
        {
            "id": "format_response",
            "type": "llm",
            "prompt": "Format a response to the user. They reported: {user_input}. We created ticket {ticket_id}.",
            "input": ["user_input", "ticket_id"],
            "output": ["result"],
        },
    ],
    "edges": [
        {"from": "search_kb", "to": "create_ticket"},
        {"from": "create_ticket", "to": "format_response"},
    ],
    "tools": [
        {
            "name": "search_kb",
            "description": "Search internal knowledge base",
            "requires_approval": False,
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "transport": "local",
        },
        {
            "name": "create_ticket",
            "description": "Create support ticket",
            "requires_approval": True,
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["summary", "body"],
            },
            "transport": "local",
        },
    ],
    "tests": [
        {
            "name": "creates_ticket_for_user_issue",
            "input": {
                "user_input": "Production server is down",
                "kb_results": [],
                "ticket_id": None,
                "result": "",
            },
            "assertions": [
                {"type": "tool_called", "name": "search_kb"},
                {"type": "tool_called", "name": "create_ticket"},
                {"type": "state_contains", "path": "ticket_id"},
            ],
            "mocks": {
                "search_kb": {"results": []},
                "create_ticket": {"ticket_id": "MOCK-123"},
            },
        }
    ],
    "runtime": {"max_steps": 10, "budget_usd": 1.00, "timeout_seconds": 30},
}


EXAMPLE_EMAIL_AGENT = {
    "name": "Email Notification Agent",
    "description": "Sends formatted email notifications",
    "model": "qwen/qwen3-coder-30b",
    "state": [
        {"name": "recipient", "type": "str"},
        {"name": "subject", "type": "str"},
        {"name": "body", "type": "str"},
        {"name": "sent", "type": "bool"},
    ],
    "nodes": [
        {
            "id": "send_email",
            "type": "tool",
            "tool": "send_email",
            "input": ["recipient", "subject", "body"],
            "output": ["sent"],
            "input_mapping": {
                "to": "recipient",
                "subject": "subject",
                "body": "body",
            },
        }
    ],
    "edges": [],
    "tools": [
        {
            "name": "send_email",
            "description": "Send email via SMTP",
            "requires_approval": False,
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
            "transport": "local",
        }
    ],
    "tests": [
        {
            "name": "sends_email_successfully",
            "input": {
                "recipient": "test@example.com",
                "subject": "Test",
                "body": "Hello",
                "sent": False,
            },
            "assertions": [
                {"type": "tool_called", "name": "send_email"},
                {"type": "state_contains", "path": "sent", "value": True},
            ],
            "mocks": {"send_email": {"sent": True}},
        }
    ],
    "runtime": {"max_steps": 5, "budget_usd": 0.50, "timeout_seconds": 15},
}
