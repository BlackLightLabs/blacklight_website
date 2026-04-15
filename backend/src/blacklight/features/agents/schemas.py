"""
Agent-related Pydantic schemas.

This module contains all Pydantic models for agent creation, execution,
and chat interactions. These schemas define the request/response models
used by the agent API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    FAILED = "failed"


class Message(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentCreateRequest(BaseModel):
    description: str = Field(
        ...,
        description="Natural language description of the agent's purpose and capabilities",
        examples=["I want an agent that checks my email daily for potential sales prospects, and continues down the sales pipeline"],
    )
    user_id: str | None = Field(None, description="User ID for tracking and billing")


class AgentCreateResponse(BaseModel):
    agent_id: str = Field(..., description="Unique identifier for the created agent")
    status: AgentStatus
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_cost_per_run: float | None = Field(
        None, description="Estimated cost in USD per execution"
    )


class AgentDetails(BaseModel):
    agent_id: str
    status: AgentStatus
    description: str
    created_at: datetime
    graph_structure: dict[str, Any] | None = Field(
        None, description="LangGraph structure of the agent"
    )
    estimated_cost_per_run: float | None = None
    total_executions: int = 0
    total_cost: float = 0.0


class ChatMessage(BaseModel):
    """Message in the agent creation chat"""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Request to continue agent creation conversation"""

    agent_id: str | None = Field(None, description="Existing agent ID if continuing conversation")
    message: str = Field(..., description="User's message")
    conversation_history: list[ChatMessage] | None = Field(
        default_factory=list, description="Previous messages in the conversation"
    )


class ChatResponse(BaseModel):
    """Response from agent creation chat"""

    agent_id: str | None = Field(None, description="Agent ID if agent is being created")
    message: str = Field(..., description="Assistant's response")
    agent_ready: bool = Field(False, description="Whether the agent is ready to use")
    agent_details: AgentDetails | None = None


# Build system schemas

class BuildStatus(str, Enum):
    """Build status enumeration"""

    PENDING = "pending"
    BUILDING = "building"
    BUILT = "built"
    TESTING = "testing"
    READY = "ready"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class AgentVersionResponse(BaseModel):
    """Response model for agent version"""

    id: str = Field(..., description="Version ID")
    agent_id: str = Field(..., description="Agent ID")
    version: int = Field(..., description="Version number")
    build_status: BuildStatus = Field(..., description="Build status")
    code_path: str | None = Field(None, description="Path to generated code")
    metrics: dict[str, Any] | None = Field(None, description="Build and test metrics")
    error_details: dict[str, Any] | None = Field(None, description="Error details if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class BuildLogResponse(BaseModel):
    """Response model for build log entry"""

    id: str = Field(..., description="Log entry ID")
    stage: str = Field(..., description="Build stage (compile, test, fixpass)")
    level: str = Field(..., description="Log level (INFO, WARN, ERROR, DEBUG)")
    message: str = Field(..., description="Log message")
    created_at: datetime = Field(..., description="Timestamp")


class TestRunResponse(BaseModel):
    """Response model for test run"""

    id: str = Field(..., description="Test run ID")
    status: str = Field(..., description="Test status (PENDING, RUNNING, PASSED, FAILED)")
    report: dict[str, Any] | None = Field(None, description="Detailed test report")
    created_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")


class BuildTriggerRequest(BaseModel):
    """Request to trigger a build"""

    force: bool = Field(False, description="Force rebuild even if version exists")


class BuildTriggerResponse(BaseModel):
    """Response from build trigger"""

    version_id: str = Field(..., description="Version ID")
    status: BuildStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")
