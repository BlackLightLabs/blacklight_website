"""
Execution models for database storage

Contains the Execution ORM model and ExecutionStatusEnum for tracking
agent execution records and their lifecycle.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.blacklight.common.base_repository import Base

if TYPE_CHECKING:
    from src.blacklight.features.agents.models import Agent


class ExecutionStatusEnum(str, enum.Enum):
    """Execution status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Execution(Base):
    """
    Execution database model

    Tracks individual agent executions, including inputs, outputs, costs,
    and execution status.
    """

    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), index=True)
    status: Mapped[ExecutionStatusEnum] = mapped_column(
        Enum(ExecutionStatusEnum), default=ExecutionStatusEnum.PENDING
    )
    input_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    output_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    error_message: Mapped[str | None] = mapped_column(String, default=None)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="executions")

    def __repr__(self):
        return f"<Execution(id={self.id}, agent_id={self.agent_id}, status={self.status})>"
