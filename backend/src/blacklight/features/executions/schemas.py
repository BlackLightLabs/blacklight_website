"""
Execution API schemas for request/response validation

Pydantic models for agent execution endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentExecuteRequest(BaseModel):
    """Request schema for executing an agent"""

    agent_id: str = Field(..., description="ID of the agent to execute")
    input_data: dict[str, Any] | None = Field(
        default_factory=dict, description="Input data for the agent execution"
    )
    user_id: str | None = Field(None, description="User ID for billing")


class AgentExecuteResponse(BaseModel):
    """Response schema for agent execution"""

    execution_id: str = Field(..., description="Unique identifier for this execution")
    agent_id: str
    status: str = Field(..., description="Execution status")
    result: dict[str, Any] | None = Field(None, description="Execution result")
    cost: float | None = Field(None, description="Actual cost of execution in USD")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
