"""
Agent and Conversation Repositories

This module contains repository classes for managing agent and conversation data:
- AgentRepository: CRUD operations for agents, status updates, and user-specific queries
- ConversationRepository: Management of conversations and their associated messages
- AgentVersionRepository: Management of agent builds and versions
- AgentBuildLogRepository: Build and test log management
- AgentTestRunRepository: Test execution tracking
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.base_repository import BaseRepository
from src.blacklight.features.agents.models import (
    Agent,
    AgentStatusEnum,
    AgentVersion,
    BuildStatusEnum,
    AgentBuildLog,
    AgentTestRun,
    Conversation,
    Message,
)


class AgentRepository(BaseRepository[Agent]):
    """
    Repository for Agent model operations.

    Provides specialized methods for agent-specific queries and updates
    beyond the base CRUD operations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the Agent model"""
        super().__init__(Agent, db)

    async def create_agent(
        self,
        agent_id: str,
        description: str,
        spec: dict,
        user_id: int,
        status: AgentStatusEnum = AgentStatusEnum.CREATING,
        estimated_cost_per_run: float = 0.10,
    ) -> Agent:
        """
        Create a new agent.

        Args:
            agent_id: Unique agent identifier
            description: Agent description
            spec: Agent specification dictionary
            user_id: ID of the user creating the agent
            status: Initial agent status
            estimated_cost_per_run: Estimated cost per execution

        Returns:
            The created Agent instance
        """
        return await self.create(
            id=agent_id,
            status=status,
            description=description,
            spec=spec,
            user_id=user_id,
            estimated_cost_per_run=estimated_cost_per_run,
        )

    async def get_ready_agents(self) -> list[Agent]:
        """
        Get all agents with READY status.

        Returns:
            List of ready agents
        """
        stmt = select(Agent).filter(Agent.status == AgentStatusEnum.READY)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, agent_id: str, status: AgentStatusEnum) -> Agent | None:
        """
        Update agent status.

        Args:
            agent_id: The agent ID
            status: New status

        Returns:
            Updated agent or None if not found
        """
        return await self.update(agent_id, status=status)

    async def increment_executions(self, agent_id: str, cost: float) -> Agent | None:
        """
        Increment execution count and add cost to total.

        Note: Does not commit. Caller must commit the transaction.

        Args:
            agent_id: The agent ID
            cost: Cost to add

        Returns:
            Updated agent or None if not found
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.total_executions += 1
            agent.total_cost += cost
            agent.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(agent)
        return agent

    async def store_graph_data(self, agent_id: str, graph_data: dict) -> Agent | None:
        """
        Store serialized LangGraph data for an agent.

        Args:
            agent_id: The agent ID
            graph_data: Serialized graph data

        Returns:
            Updated agent or None if not found
        """
        return await self.update(agent_id, graph_data=graph_data)

    async def get_by_user_id(self, user_id: int) -> list[Agent]:
        """
        Get all agents created by a specific user.

        Args:
            user_id: The user ID

        Returns:
            List of agents owned by the user
        """
        stmt = select(Agent).filter(Agent.user_id == user_id).order_by(Agent.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_and_user(self, agent_id: str, user_id: int) -> Agent | None:
        """
        Get an agent by ID, ensuring it belongs to the specified user.

        Args:
            agent_id: The agent ID
            user_id: The user ID

        Returns:
            Agent if found and owned by user, None otherwise
        """
        stmt = select(Agent).filter(Agent.id == agent_id, Agent.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class ConversationRepository(BaseRepository[Conversation]):
    """
    Repository for Conversation model operations.

    Manages conversations and their associated messages.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the Conversation model"""
        super().__init__(Conversation, db)

    async def create_conversation(
        self, agent_id: str, user_id: int, conversation_id: str | None = None
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            agent_id: ID of the associated agent
            user_id: ID of the user creating the conversation
            conversation_id: Optional conversation ID (generated if not provided)

        Returns:
            The created Conversation instance
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        return await self.create(id=conversation_id, agent_id=agent_id, user_id=user_id)

    async def get_by_agent_id(self, agent_id: str) -> list[Conversation]:
        """
        Get all conversations for a specific agent.

        Args:
            agent_id: The agent ID

        Returns:
            List of conversations
        """
        stmt = select(Conversation).filter(Conversation.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(self, conversation_id: str, role: str, content: str) -> Message | None:
        """
        Add a message to a conversation.

        Args:
            conversation_id: The conversation ID
            role: Message role ("user" or "assistant")
            content: Message content

        Returns:
            The created Message instance or None if conversation not found
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return None

        message = Message(
            id=str(uuid.uuid4()), conversation_id=conversation_id, role=role, content=content
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        await self.db.commit()

        return message

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of messages ordered by timestamp
        """
        stmt = (
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_conversation(
        self, agent_id: str, user_id: int, conversation_id: str | None = None
    ) -> Conversation:
        """
        Get an existing conversation or create a new one.

        Args:
            agent_id: The agent ID
            user_id: The user ID
            conversation_id: Optional conversation ID to retrieve

        Returns:
            Existing or newly created Conversation instance
        """
        if conversation_id:
            conversation = await self.get_by_id(conversation_id)
            if conversation:
                return conversation

        return await self.create_conversation(agent_id, user_id, conversation_id)


class AgentVersionRepository(BaseRepository[AgentVersion]):
    """
    Repository for AgentVersion model operations.

    Manages agent builds, versions, and their lifecycle.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the AgentVersion model"""
        super().__init__(AgentVersion, db)

    async def create_version(
        self,
        agent_id: str,
        spec: dict,
        version: int | None = None,
    ) -> AgentVersion:
        """
        Create a new agent version.

        Args:
            agent_id: Agent ID
            spec: Agent specification
            version: Version number (auto-incremented if not provided)

        Returns:
            Created AgentVersion instance
        """
        if version is None:
            # Get latest version for this agent
            version = await self.get_latest_version_number(agent_id)
            version = (version or 0) + 1

        version_id = str(uuid.uuid4())
        return await self.create(
            id=version_id,
            agent_id=agent_id,
            version=version,
            spec=spec,
            build_status=BuildStatusEnum.PENDING,
        )

    async def get_latest_version_number(self, agent_id: str) -> int | None:
        """
        Get the latest version number for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Latest version number or None if no versions exist
        """
        stmt = (
            select(AgentVersion.version)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_version(self, agent_id: str) -> AgentVersion | None:
        """
        Get the latest version for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Latest AgentVersion or None
        """
        stmt = (
            select(AgentVersion)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_versions_by_agent(self, agent_id: str) -> list[AgentVersion]:
        """
        Get all versions for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of AgentVersions ordered by version descending
        """
        stmt = (
            select(AgentVersion)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_build_status(
        self, version_id: str, status: BuildStatusEnum, **kwargs
    ) -> AgentVersion | None:
        """
        Update build status and optional fields.

        Args:
            version_id: Version ID
            status: New build status
            **kwargs: Additional fields to update

        Returns:
            Updated AgentVersion or None
        """
        return await self.update(version_id, build_status=status, **kwargs)


class AgentBuildLogRepository(BaseRepository[AgentBuildLog]):
    """
    Repository for AgentBuildLog model operations.

    Manages build and test logs for agent versions.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the AgentBuildLog model"""
        super().__init__(AgentBuildLog, db)

    async def add_log(
        self,
        agent_version_id: str,
        stage: str,
        level: str,
        message: str,
    ) -> AgentBuildLog:
        """
        Add a build log entry.

        Args:
            agent_version_id: Version ID
            stage: Build stage (compile, test, fixpass)
            level: Log level (INFO, WARN, ERROR, DEBUG)
            message: Log message

        Returns:
            Created AgentBuildLog instance
        """
        log_id = str(uuid.uuid4())
        return await self.create(
            id=log_id,
            agent_version_id=agent_version_id,
            stage=stage,
            level=level,
            message=message,
        )

    async def get_logs_by_version(
        self, agent_version_id: str, stage: str | None = None
    ) -> list[AgentBuildLog]:
        """
        Get all logs for a version.

        Args:
            agent_version_id: Version ID
            stage: Optional stage filter

        Returns:
            List of AgentBuildLogs ordered by timestamp
        """
        stmt = select(AgentBuildLog).filter(
            AgentBuildLog.agent_version_id == agent_version_id
        )

        if stage:
            stmt = stmt.filter(AgentBuildLog.stage == stage)

        stmt = stmt.order_by(AgentBuildLog.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class AgentTestRunRepository(BaseRepository[AgentTestRun]):
    """
    Repository for AgentTestRun model operations.

    Manages test execution results for agent versions.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the AgentTestRun model"""
        super().__init__(AgentTestRun, db)

    async def create_test_run(self, agent_version_id: str) -> AgentTestRun:
        """
        Create a new test run.

        Args:
            agent_version_id: Version ID

        Returns:
            Created AgentTestRun instance
        """
        test_run_id = str(uuid.uuid4())
        return await self.create(
            id=test_run_id,
            agent_version_id=agent_version_id,
            status="PENDING",
        )

    async def update_test_run(
        self,
        test_run_id: str,
        status: str,
        report: dict | None = None,
        completed_at: datetime | None = None,
    ) -> AgentTestRun | None:
        """
        Update test run with results.

        Args:
            test_run_id: Test run ID
            status: Test status (PENDING, RUNNING, PASSED, FAILED)
            report: Test report JSON
            completed_at: Completion timestamp

        Returns:
            Updated AgentTestRun or None
        """
        update_data: dict[str, Any] = {"status": status}
        if report is not None:
            update_data["report"] = report
        if completed_at is not None:
            update_data["completed_at"] = completed_at

        return await self.update(test_run_id, **update_data)

    async def get_latest_test_run(self, agent_version_id: str) -> AgentTestRun | None:
        """
        Get the latest test run for a version.

        Args:
            agent_version_id: Version ID

        Returns:
            Latest AgentTestRun or None
        """
        stmt = (
            select(AgentTestRun)
            .filter(AgentTestRun.agent_version_id == agent_version_id)
            .order_by(AgentTestRun.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
