"""
Unit tests for repository layer

Tests CRUD operations, edge cases, and database interactions.
"""

from src.blacklight.features.agents.models import AgentStatusEnum
from src.blacklight.features.executions.models import ExecutionStatusEnum


class TestAgentRepository:
    """Tests for AgentRepository"""

    async def test_create_agent(self, async_agent_repo, sample_agent_data, test_user_id):
        """Test creating a new agent"""
        agent = await async_agent_repo.create_agent(
            agent_id=sample_agent_data["agent_id"],
            description=sample_agent_data["description"],
            spec=sample_agent_data["spec"],
            user_id=test_user_id,
        )

        assert agent.id == sample_agent_data["agent_id"]
        assert agent.description == sample_agent_data["description"]
        assert agent.status == AgentStatusEnum.CREATING
        assert agent.total_executions == 0
        assert agent.total_cost == 0.0

    async def test_get_agent_by_id(self, async_agent_repo, sample_agent_data, test_user_id):
        """Test retrieving agent by ID"""
        # Create agent
        created = await async_agent_repo.create_agent(
            agent_id=sample_agent_data["agent_id"],
            description=sample_agent_data["description"],
            spec=sample_agent_data["spec"],
            user_id=test_user_id,
        )

        # Retrieve agent
        retrieved = await async_agent_repo.get_by_id(sample_agent_data["agent_id"])

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == created.description

    async def test_get_nonexistent_agent(self, async_agent_repo, test_user_id):
        """Test retrieving non-existent agent returns None"""
        agent = await async_agent_repo.get_by_id("nonexistent-id")
        assert agent is None

    async def test_update_agent_status(self, async_agent_repo, sample_agent_data, test_user_id):
        """Test updating agent status"""
        # Create agent
        await async_agent_repo.create_agent(
            agent_id=sample_agent_data["agent_id"],
            description=sample_agent_data["description"],
            spec=sample_agent_data["spec"],
            user_id=test_user_id,
        )

        # Update status
        updated = await async_agent_repo.update_status(sample_agent_data["agent_id"], AgentStatusEnum.READY)

        assert updated is not None
        assert updated.status == AgentStatusEnum.READY

    async def test_increment_executions(self, async_agent_repo, sample_agent_data, test_user_id):
        """Test incrementing execution count and cost"""
        # Create agent
        await async_agent_repo.create_agent(
            agent_id=sample_agent_data["agent_id"],
            description=sample_agent_data["description"],
            spec=sample_agent_data["spec"],
            user_id=test_user_id,
        )

        # Increment executions
        updated = await async_agent_repo.increment_executions(sample_agent_data["agent_id"], cost=0.50)

        assert updated is not None
        assert updated.total_executions == 1
        assert updated.total_cost == 0.50

        # Increment again
        updated = await async_agent_repo.increment_executions(sample_agent_data["agent_id"], cost=0.75)

        assert updated.total_executions == 2
        assert updated.total_cost == 1.25

    async def test_get_ready_agents(self, async_agent_repo, test_user_id):
        """Test getting all ready agents"""
        # Create agents with different statuses
        await async_agent_repo.create_agent(
            agent_id="ready-1", description="Ready agent 1", spec={}, status=AgentStatusEnum.READY, user_id=test_user_id
        )
        await async_agent_repo.create_agent(
            agent_id="ready-2", description="Ready agent 2", spec={}, status=AgentStatusEnum.READY, user_id=test_user_id
        )
        await async_agent_repo.create_agent(
            agent_id="creating-1",
            description="Creating agent",
            spec={},
            status=AgentStatusEnum.CREATING,
            user_id=test_user_id,
        )

        ready_agents = await async_agent_repo.get_ready_agents()

        assert len(ready_agents) == 2
        assert all(agent.status == AgentStatusEnum.READY for agent in ready_agents)


class TestConversationRepository:
    """Tests for ConversationRepository"""

    async def test_create_conversation(self, async_conversation_repo, async_agent_repo, test_user_id):
        """Test creating a new conversation"""
        # Create agent first
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)

        # Create conversation
        conversation = await async_conversation_repo.create_conversation(agent_id="test-agent", user_id=test_user_id)

        assert conversation is not None
        assert conversation.agent_id == "test-agent"
        assert conversation.id is not None

    async def test_add_message_to_conversation(self, async_conversation_repo, async_agent_repo, test_user_id):
        """Test adding messages to conversation"""
        # Setup
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)
        conversation = await async_conversation_repo.create_conversation(agent_id="test-agent", user_id=test_user_id)

        # Add message
        message = await async_conversation_repo.add_message(
            conversation_id=conversation.id, role="user", content="Hello!"
        )

        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.role == "user"
        assert message.content == "Hello!"

    async def test_get_messages(self, async_conversation_repo, async_agent_repo, test_user_id):
        """Test retrieving conversation messages"""
        # Setup
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)
        conversation = await async_conversation_repo.create_conversation(agent_id="test-agent", user_id=test_user_id)

        # Add multiple messages
        await async_conversation_repo.add_message(conversation.id, "user", "Message 1")
        await async_conversation_repo.add_message(conversation.id, "assistant", "Response 1")
        await async_conversation_repo.add_message(conversation.id, "user", "Message 2")

        # Get messages
        messages = await async_conversation_repo.get_messages(conversation.id)

        assert len(messages) == 3
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Response 1"
        assert messages[2].content == "Message 2"

    async def test_get_or_create_conversation(self, async_conversation_repo, async_agent_repo, test_user_id):
        """Test get or create conversation logic"""
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)

        # First call should create
        conv1 = await async_conversation_repo.get_or_create_conversation(agent_id="test-agent", user_id=test_user_id)
        assert conv1 is not None

        # Second call with same ID should retrieve
        conv2 = await async_conversation_repo.get_or_create_conversation(
            agent_id="test-agent", conversation_id=conv1.id
        , user_id=test_user_id)
        assert conv2.id == conv1.id


class TestExecutionRepository:
    """Tests for ExecutionRepository"""

    async def test_create_execution(self, async_execution_repo, async_agent_repo, test_user_id):
        """Test creating execution record"""
        # Setup
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)

        # Create execution
        execution = await async_execution_repo.create_execution(
            agent_id="test-agent", input_data={"key": "value"}
        )

        assert execution is not None
        assert execution.agent_id == "test-agent"
        assert execution.status == ExecutionStatusEnum.PENDING
        assert execution.input_data == {"key": "value"}

    async def test_update_execution_status(self, async_execution_repo, async_agent_repo, test_user_id):
        """Test updating execution status"""
        # Setup
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)
        execution = await async_execution_repo.create_execution(agent_id="test-agent")

        # Update to running
        updated = await async_execution_repo.update_status(execution.id, ExecutionStatusEnum.RUNNING)
        assert updated.status == ExecutionStatusEnum.RUNNING

        # Update to completed with output
        updated = await async_execution_repo.update_status(
            execution.id, ExecutionStatusEnum.COMPLETED, output_data={"result": "success"}
        )
        assert updated.status == ExecutionStatusEnum.COMPLETED
        assert updated.output_data == {"result": "success"}
        assert updated.completed_at is not None

    async def test_set_execution_cost(self, async_execution_repo, async_agent_repo, test_user_id):
        """Test setting execution cost"""
        # Setup
        await async_agent_repo.create_agent(agent_id="test-agent", description="Test", spec={}, user_id=test_user_id)
        execution = await async_execution_repo.create_execution(agent_id="test-agent")

        # Set cost
        updated = await async_execution_repo.set_cost(execution.id, 0.75)

        assert updated.cost == 0.75

    async def test_get_executions_by_agent(self, async_execution_repo, async_agent_repo, test_user_id):
        """Test getting executions for specific agent"""
        # Setup
        await async_agent_repo.create_agent(agent_id="agent-1", description="Test 1", spec={}, user_id=test_user_id)
        await async_agent_repo.create_agent(agent_id="agent-2", description="Test 2", spec={}, user_id=test_user_id)

        # Create executions
        await async_execution_repo.create_execution(agent_id="agent-1")
        await async_execution_repo.create_execution(agent_id="agent-1")
        await async_execution_repo.create_execution(agent_id="agent-2")

        # Get executions for agent-1
        executions = await async_execution_repo.get_by_agent_id("agent-1")

        assert len(executions) == 2
        assert all(ex.agent_id == "agent-1" for ex in executions)
