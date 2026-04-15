"""
Agent domain models for database storage.

This module contains all database models related to agents and their interactions:
- AgentStatusEnum: Enumeration of possible agent states
- Agent: AI agent configurations with LangGraph specifications and metrics
- Conversation: Chat sessions between users and the agent builder AI
- Message: Individual messages within conversations
- BuildStatusEnum: Enumeration of agent build states
- AgentVersion: Versioned agent builds with code and test results
- AgentBuildLog: Build and test execution logs
- AgentTestRun: Test execution results with detailed reports
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.blacklight.common.base_repository import Base

if TYPE_CHECKING:
    from src.blacklight.features.auth.models import User
    from src.blacklight.features.executions.models import Execution


class AgentStatusEnum(str, enum.Enum):
    """Agent status enumeration"""

    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    FAILED = "failed"


class Agent(Base):
    """
    Agent database model

    Stores AI agent configurations, including their LangGraph specifications,
    execution history, and cost tracking.
    """

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )  # Owner of the agent
    status: Mapped[AgentStatusEnum] = mapped_column(
        Enum(AgentStatusEnum), default=AgentStatusEnum.CREATING
    )
    description: Mapped[str] = mapped_column(String)
    spec: Mapped[dict] = mapped_column(JSON)  # Agent specification (steps, inputs, outputs, etc.)
    graph_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Serialized LangGraph data
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Metrics
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_per_run: Mapped[float] = mapped_column(Float, default=0.10)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="agents")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="agent", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Agent(id={self.id}, status={self.status}, description={self.description[:50]})>"


class Conversation(Base):
    """
    Conversation database model

    Tracks conversation sessions between users and the agent builder AI.
    Each conversation can have multiple messages and is associated with one agent.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )  # Owner of the conversation
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    agent: Mapped["Agent"] = relationship("Agent", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.timestamp",
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, agent_id={self.agent_id})>"


class Message(Base):
    """
    Message database model

    Stores individual messages within a conversation, tracking both user
    messages and AI assistant responses.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class BuildStatusEnum(str, enum.Enum):
    """Build status enumeration for agent versions"""

    PENDING = "pending"
    BUILDING = "building"
    BUILT = "built"
    TESTING = "testing"
    READY = "ready"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class AgentVersion(Base):
    """
    Agent version model

    Stores versioned builds of agents with their specs, generated code paths,
    build status, and test metrics. Enables version history and rollback.
    """

    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)  # Monotonic per agent
    spec: Mapped[dict] = mapped_column(JSON)  # Frozen spec used for this build
    code_path: Mapped[str | None] = mapped_column(String, nullable=True)  # Path to generated code
    build_status: Mapped[BuildStatusEnum] = mapped_column(
        Enum(BuildStatusEnum), default=BuildStatusEnum.PENDING
    )
    metrics: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Build/test metrics, cost estimates
    error_details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Error info if build/test failed
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", backref="versions")
    build_logs: Mapped[list["AgentBuildLog"]] = relationship(
        "AgentBuildLog", back_populates="version", cascade="all, delete-orphan"
    )
    test_runs: Mapped[list["AgentTestRun"]] = relationship(
        "AgentTestRun", back_populates="version", cascade="all, delete-orphan"
    )
    diffs_from: Mapped[list["AgentVersionDiff"]] = relationship(
        "AgentVersionDiff",
        foreign_keys="AgentVersionDiff.from_version_id",
        back_populates="from_version",
        cascade="all, delete-orphan",
    )
    diffs_to: Mapped[list["AgentVersionDiff"]] = relationship(
        "AgentVersionDiff",
        foreign_keys="AgentVersionDiff.to_version_id",
        back_populates="to_version",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<AgentVersion(id={self.id}, agent_id={self.agent_id}, version={self.version}, status={self.build_status})>"


class AgentBuildLog(Base):
    """
    Agent build log model

    Stores timestamped logs from the build and test process for debugging
    and observability. Each log entry has a stage (compile, test, fixpass),
    level (INFO, WARN, ERROR), and message.
    """

    __tablename__ = "agent_build_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_versions.id"), index=True
    )
    stage: Mapped[str] = mapped_column(String)  # "compile", "test", "fixpass"
    level: Mapped[str] = mapped_column(String)  # "INFO", "WARN", "ERROR", "DEBUG"
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Relationships
    version: Mapped["AgentVersion"] = relationship("AgentVersion", back_populates="build_logs")

    def __repr__(self):
        return f"<AgentBuildLog(id={self.id}, stage={self.stage}, level={self.level})>"


class AgentTestRun(Base):
    """
    Agent test run model

    Stores test execution results with detailed reports including pass/fail
    status per test case, traces, and performance metrics.
    """

    __tablename__ = "agent_test_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    agent_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_versions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String)  # "PENDING", "RUNNING", "PASSED", "FAILED"
    report: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Detailed test report with cases and traces
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    version: Mapped["AgentVersion"] = relationship("AgentVersion", back_populates="test_runs")

    def __repr__(self):
        return f"<AgentTestRun(id={self.id}, version_id={self.agent_version_id}, status={self.status})>"


class PromptTemplateType(str, enum.Enum):
    """Prompt template type enumeration"""

    SYSTEM = "system"  # System-level prompts
    USER = "user"  # User-defined custom prompts
    AGENT = "agent"  # Agent-specific prompts
    REVISION = "revision"  # Self-repair revision prompts


class PromptTemplate(Base):
    """
    Prompt Template model

    Stores versioned prompt templates for agent creation, revision, and customization.
    Supports Jinja2 template syntax with variables.
    """

    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    template_type: Mapped[PromptTemplateType] = mapped_column(
        Enum(PromptTemplateType), default=PromptTemplateType.SYSTEM, index=True
    )
    content: Mapped[str] = mapped_column(Text)  # Jinja2 template content
    variables: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Expected variables: {"tool_catalog": "str", "example_spec": "str"}
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Human-readable description
    version: Mapped[int] = mapped_column(Integer, default=1)  # Template version
    is_active: Mapped[int] = mapped_column(
        Integer, default=1
    )  # 1 for active, 0 for inactive (using Integer for SQLite compatibility)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who created (null for system)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name={self.name}, type={self.template_type}, version={self.version})>"


class AgentVersionDiff(Base):
    """
    Agent Version Diff model

    Stores differences between agent versions for comparison and self-repair tracking.
    Records what changed between spec revisions.
    """

    __tablename__ = "agent_version_diffs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    from_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_versions.id"), index=True
    )
    to_version_id: Mapped[str] = mapped_column(String, ForeignKey("agent_versions.id"), index=True)
    diff_type: Mapped[str] = mapped_column(String(50))  # "spec_change", "retry_fix", "manual_edit"
    changes: Mapped[dict] = mapped_column(
        JSON
    )  # Structured diff: {"nodes": {"added": [...], "removed": [...]}, ...}
    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Why the change was made (e.g., "Fixed edge format")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Relationships
    from_version: Mapped["AgentVersion"] = relationship(
        "AgentVersion", foreign_keys=[from_version_id], back_populates="diffs_from"
    )
    to_version: Mapped["AgentVersion"] = relationship(
        "AgentVersion", foreign_keys=[to_version_id], back_populates="diffs_to"
    )

    def __repr__(self):
        return f"<AgentVersionDiff(id={self.id}, from={self.from_version_id}, to={self.to_version_id}, type={self.diff_type})>"
