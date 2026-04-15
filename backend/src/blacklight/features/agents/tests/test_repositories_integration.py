"""
Integration tests for repositories with real database

These tests use an in-memory SQLite database to test repository operations.
"""

from src.blacklight.features.agents.models import AgentStatusEnum
from src.blacklight.features.agents.repositories import AgentRepository, ConversationRepository


class TestAgentRepository:
    """Integration tests for AgentRepository"""

    async def test_create_agent(self, async_db, test_user_id):
        """Test creating an agent"""
        repo = AgentRepository(async_db)

        agent = await repo.create_agent(
            agent_id="test-123",
            description="Test agent",
            spec={"name": "test"},
            status=AgentStatusEnum.CREATING,
            user_id=test_user_id,
        )

        assert agent.id == "test-123"
        assert agent.description == "Test agent"
        assert agent.status == AgentStatusEnum.CREATING

    async def test_get_by_id(self, async_db, test_user_id):
        """Test retrieving agent by ID"""
        repo = AgentRepository(async_db)

        # Create agent
        created = await repo.create_agent(
            agent_id="test-456", description="Another test", spec={}, status=AgentStatusEnum.READY, user_id=test_user_id
        )

        # Retrieve agent
        retrieved = await repo.get_by_id("test-456")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == "Another test"

    async def test_update_agent(self, async_db, test_user_id):
        """Test updating an agent"""
        repo = AgentRepository(async_db)

        # Create agent
        await repo.create_agent(
            agent_id="test-789", description="Original", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id
        )

        # Update agent
        updated = await repo.update(
            "test-789",  # ID as positional argument
            status=AgentStatusEnum.READY,
            description="Updated description",
            spec={"name": "updated"},
        )

        assert updated.status == AgentStatusEnum.READY
        assert updated.description == "Updated description"
        assert updated.spec["name"] == "updated"

    async def test_get_all(self, async_db, test_user_id):
        """Test retrieving all agents"""
        repo = AgentRepository(async_db)

        # Create multiple agents
        await repo.create_agent(agent_id="agent-1", description="Agent 1", spec={}, status=AgentStatusEnum.READY, user_id=test_user_id)
        await repo.create_agent(agent_id="agent-2", description="Agent 2", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)
        await repo.create_agent(agent_id="agent-3", description="Agent 3", spec={}, status=AgentStatusEnum.FAILED, user_id=test_user_id)

        # Retrieve all
        agents = await repo.get_all()

        assert len(agents) == 3
        assert {a.id for a in agents} == {"agent-1", "agent-2", "agent-3"}


class TestConversationRepository:
    """Integration tests for ConversationRepository"""

    async def test_create_conversation(self, async_db, test_user_id):
        """Test creating a conversation"""
        # First create an agent
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-1", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        # Create conversation
        conv_repo = ConversationRepository(async_db)
        conversation = await conv_repo.create_conversation(agent_id="agent-1", user_id=test_user_id)

        assert conversation.agent_id == "agent-1"
        assert conversation.id is not None

    async def test_get_or_create_conversation_creates_new(self, async_db, test_user_id):
        """Test get_or_create when conversation doesn't exist"""
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-2", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        conv_repo = ConversationRepository(async_db)
        conversation = await conv_repo.get_or_create_conversation(agent_id="agent-2", user_id=test_user_id)

        assert conversation.agent_id == "agent-2"

    async def test_get_or_create_conversation_returns_existing(self, async_db, test_user_id):
        """Test get_or_create when conversation exists"""
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-3", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        conv_repo = ConversationRepository(async_db)

        # Create conversation
        created = await conv_repo.create_conversation(agent_id="agent-3", conversation_id="conv-123", user_id=test_user_id)

        # Try to get it
        retrieved = await conv_repo.get_or_create_conversation(
            agent_id="agent-3", conversation_id="conv-123", user_id=test_user_id
        )

        assert retrieved.id == created.id
        assert retrieved.id == "conv-123"

    async def test_add_message(self, async_db, test_user_id):
        """Test adding a message to a conversation"""
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-4", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        conv_repo = ConversationRepository(async_db)
        conversation = await conv_repo.create_conversation(agent_id="agent-4", user_id=test_user_id)

        # Add message
        message = await conv_repo.add_message(
            conversation_id=conversation.id, role="user", content="Hello!"
        )

        assert message is not None
        assert message.role == "user"
        assert message.content == "Hello!"
        assert message.conversation_id == conversation.id

    async def test_get_messages(self, async_db, test_user_id):
        """Test retrieving messages for a conversation"""
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-5", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        conv_repo = ConversationRepository(async_db)
        conversation = await conv_repo.create_conversation(agent_id="agent-5", user_id=test_user_id)

        # Add multiple messages
        await conv_repo.add_message(conversation.id, "user", "First message")
        await conv_repo.add_message(conversation.id, "assistant", "Second message")
        await conv_repo.add_message(conversation.id, "user", "Third message")

        # Retrieve messages
        messages = await conv_repo.get_messages(conversation.id)

        assert len(messages) == 3
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"
        assert messages[2].content == "Third message"
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    async def test_get_by_agent_id(self, async_db, test_user_id):
        """Test retrieving all conversations for an agent"""
        async_agent_repo = AgentRepository(async_db)
        await async_agent_repo.create_agent(agent_id="agent-6", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id)

        conv_repo = ConversationRepository(async_db)

        # Create multiple conversations
        conv1 = await conv_repo.create_conversation(agent_id="agent-6", user_id=test_user_id)
        conv2 = await conv_repo.create_conversation(agent_id="agent-6", user_id=test_user_id)

        # Retrieve all
        conversations = await conv_repo.get_by_agent_id("agent-6")

        assert len(conversations) == 2
        assert {c.id for c in conversations} == {conv1.id, conv2.id}


class TestConversationPersistence:
    """Test that conversations persist properly in database"""

    async def test_full_conversation_flow(self, async_db, test_user_id):
        """Test creating an agent, conversation, and messages"""
        # Create agent
        async_agent_repo = AgentRepository(async_db)
        agent = await async_agent_repo.create_agent(
            agent_id="full-test",
            description="Full test agent",
            spec={"name": "test"},
            status=AgentStatusEnum.CREATING,
            user_id=test_user_id,
        )

        # Create conversation
        conv_repo = ConversationRepository(async_db)
        conversation = await conv_repo.create_conversation(agent_id=agent.id, user_id=test_user_id)

        # Add messages
        await conv_repo.add_message(conversation.id, "user", "I want to create an agent")
        await conv_repo.add_message(conversation.id, "assistant", "I can help with that!")
        await conv_repo.add_message(conversation.id, "user", "Great!")

        # Verify everything
        retrieved_agent = await async_agent_repo.get_by_id("full-test")
        assert retrieved_agent is not None

        retrieved_conversations = await conv_repo.get_by_agent_id("full-test")
        assert len(retrieved_conversations) == 1

        messages = await conv_repo.get_messages(conversation.id)
        assert len(messages) == 3
        assert all(m.conversation_id == conversation.id for m in messages)
