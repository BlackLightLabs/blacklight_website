"""
Unit tests for AgentBuilderService with mocked repositories

These tests mock the repository layer entirely to test service logic in isolation.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.blacklight.features.agents.models import Agent, AgentStatusEnum, Conversation, Message
from src.blacklight.features.agents.services import AgentBuilderService


@pytest.fixture
def mock_agent_repo():
    """Create a mock AgentRepository"""
    repo = Mock()
    repo.create_agent = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_id_and_user = AsyncMock()
    repo.update = AsyncMock()
    repo.get_all = AsyncMock()
    repo.get_all_by_user = AsyncMock()
    repo.get_by_user_id = AsyncMock()
    return repo


@pytest.fixture
def mock_conversation_repo():
    """Create a mock ConversationRepository"""
    repo = Mock()
    repo.get_or_create_conversation = AsyncMock()
    repo.add_message = AsyncMock()
    repo.get_messages = AsyncMock()
    return repo


@pytest.fixture
def service(mock_agent_repo, mock_conversation_repo):
    """Create AgentBuilderService with mocked repositories"""
    with patch("src.blacklight.features.agents.services.LLMConfig.get_llm"):
        service = AgentBuilderService(
            agent_repository=mock_agent_repo, conversation_repository=mock_conversation_repo
        )
        return service


class TestChatForAgentCreation:
    """Test chat_for_agent_creation method"""

    @pytest.mark.asyncio
    async def test_creates_new_agent_when_no_agent_id(
        self, service, mock_agent_repo, mock_conversation_repo, test_user_id
    ):
        """Test that a new agent is created when no agent_id is provided"""
        # Arrange
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = "conv-123"
        mock_conversation_repo.get_or_create_conversation.return_value = mock_conversation
        mock_conversation_repo.add_message.return_value = Mock(spec=Message)
        mock_conversation_repo.get_messages.return_value = []

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "I can help you build that agent!"
        service.llm = AsyncMock()
        service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Act
        agent_id, response_text, agent_ready, agent_details = await service.chat_for_agent_creation(
            message="Create an agent for me", conversation_history=None, agent_id=None, user_id=test_user_id
        )

        # Assert
        assert agent_id is not None
        assert mock_agent_repo.create_agent.called
        assert mock_conversation_repo.add_message.call_count == 2  # User + Assistant messages
        assert response_text == "I can help you build that agent!"
        assert agent_ready is False
        assert agent_details is None

    @pytest.mark.asyncio
    async def test_uses_existing_agent_when_agent_id_provided(
        self, service, mock_agent_repo, mock_conversation_repo, test_user_id
    ):
        """Test that existing agent is used when agent_id is provided"""
        # Arrange
        existing_agent_id = "existing-123"
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = "conv-123"
        mock_conversation_repo.get_or_create_conversation.return_value = mock_conversation
        mock_conversation_repo.get_messages.return_value = []

        mock_response = Mock()
        mock_response.content = "Let's continue!"
        service.llm = AsyncMock()
        service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Act
        agent_id, _, _, _ = await service.chat_for_agent_creation(
            message="Continue building", agent_id=existing_agent_id
        , user_id=test_user_id)

        # Assert
        assert agent_id == existing_agent_id
        assert not mock_agent_repo.create_agent.called

    @pytest.mark.asyncio
    async def test_stores_user_and_assistant_messages(self, service, mock_conversation_repo, test_user_id):
        """Test that both user and assistant messages are stored"""
        # Arrange
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = "conv-123"
        mock_conversation_repo.get_or_create_conversation.return_value = mock_conversation
        mock_conversation_repo.get_messages.return_value = []

        mock_response = Mock()
        mock_response.content = "Sure thing!"
        service.llm = AsyncMock()
        service.llm.ainvoke = AsyncMock(return_value=mock_response)

        user_message = "Build me an agent"

        # Act
        await service.chat_for_agent_creation(message=user_message, user_id=test_user_id)

        # Assert
        calls = mock_conversation_repo.add_message.call_args_list
        assert len(calls) == 2

        # First call should be user message
        assert calls[0][1]["role"] == "user"
        assert calls[0][1]["content"] == user_message

        # Second call should be assistant message
        assert calls[1][1]["role"] == "assistant"
        assert calls[1][1]["content"] == "Sure thing!"

    @pytest.mark.asyncio
    async def test_detects_agent_ready_signal(
        self, service, mock_agent_repo, mock_conversation_repo, test_user_id
    ):
        """Test that AGENT_READY signal triggers agent creation"""
        # Arrange
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = "conv-123"
        mock_conversation_repo.get_or_create_conversation.return_value = mock_conversation
        mock_conversation_repo.get_messages.return_value = []

        agent_spec = {
            "name": "Email Summary Agent",
            "description": "Sends daily email summaries",
            "steps": ["fetch emails", "summarize", "send"],
            "estimated_cost": 0.25,
        }

        mock_response = Mock()
        mock_response.content = f"Great! AGENT_READY: {json.dumps(agent_spec)}"
        service.llm = AsyncMock()
        service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Mock agent update
        mock_agent = Mock(spec=Agent)
        mock_agent.created_at = datetime.utcnow()
        mock_agent.total_executions = 0
        mock_agent.total_cost = 0.0
        mock_agent_repo.update.return_value = mock_agent

        # Act
        agent_id, response_text, agent_ready, agent_details = await service.chat_for_agent_creation(
            message="Yes, create it!"
        , user_id=test_user_id)

        # Assert
        assert agent_ready is True
        assert agent_details is not None
        assert agent_details.description == "Sends daily email summaries"
        assert mock_agent_repo.update.called

    @pytest.mark.asyncio
    async def test_handles_malformed_agent_spec(self, service, mock_conversation_repo, test_user_id):
        """Test graceful handling of malformed JSON in AGENT_READY"""
        # Arrange
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = "conv-123"
        mock_conversation_repo.get_or_create_conversation.return_value = mock_conversation
        mock_conversation_repo.get_messages.return_value = []

        mock_response = Mock()
        mock_response.content = "AGENT_READY: {invalid json}"
        service.llm = AsyncMock()
        service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Act
        _, response_text, agent_ready, agent_details = await service.chat_for_agent_creation(
            message="Create it"
        , user_id=test_user_id)

        # Assert
        assert agent_ready is False
        assert agent_details is None
        assert "error" in response_text.lower()


class TestGetAgent:
    """Test get_agent method"""

    async def test_returns_agent_details_when_found(self, service, mock_agent_repo, test_user_id):
        """Test that agent details are returned when agent exists"""
        # Arrange
        mock_agent = Mock(spec=Agent)
        mock_agent.id = "agent-123"
        mock_agent.status = AgentStatusEnum.READY
        mock_agent.description = "Test agent"
        mock_agent.created_at = datetime.utcnow()
        mock_agent.spec = {"name": "test"}
        mock_agent.estimated_cost_per_run = 0.10
        mock_agent.total_executions = 5
        mock_agent.total_cost = 0.50
        mock_agent_repo.get_by_id.return_value = mock_agent
        mock_agent_repo.get_by_id_and_user.return_value = mock_agent  # For RBAC

        # Act
        result = await service.get_agent("agent-123", user_id=test_user_id)

        # Assert
        assert result is not None
        assert result.agent_id == "agent-123"
        assert result.description == "Test agent"
        assert result.total_executions == 5

    async def test_returns_none_when_agent_not_found(self, service, mock_agent_repo, test_user_id):
        """Test that None is returned when agent doesn't exist"""
        # Arrange
        mock_agent_repo.get_by_id.return_value = None
        mock_agent_repo.get_by_id_and_user.return_value = None  # For RBAC

        # Act
        result = await service.get_agent("nonexistent", user_id=test_user_id)

        # Assert
        assert result is None


class TestListAgents:
    """Test list_agents method"""

    async def test_returns_all_agents(self, service, mock_agent_repo, test_user_id):
        """Test that all agents are returned"""
        # Arrange
        mock_agent1 = Mock(spec=Agent)
        mock_agent1.id = "agent-1"
        mock_agent1.status = AgentStatusEnum.READY
        mock_agent1.description = "Agent 1"
        mock_agent1.created_at = datetime.utcnow()
        mock_agent1.spec = {}
        mock_agent1.estimated_cost_per_run = 0.10
        mock_agent1.total_executions = 0
        mock_agent1.total_cost = 0.0

        mock_agent2 = Mock(spec=Agent)
        mock_agent2.id = "agent-2"
        mock_agent2.status = AgentStatusEnum.CREATING
        mock_agent2.description = "Agent 2"
        mock_agent2.created_at = datetime.utcnow()
        mock_agent2.spec = {}
        mock_agent2.estimated_cost_per_run = 0.15
        mock_agent2.total_executions = 10
        mock_agent2.total_cost = 1.50

        mock_agent_repo.get_all.return_value = [mock_agent1, mock_agent2]
        mock_agent_repo.get_by_user_id.return_value = [mock_agent1, mock_agent2]  # For RBAC

        # Act
        result = await service.list_agents(user_id=test_user_id)

        # Assert
        assert len(result) == 2
        assert result[0].agent_id == "agent-1"
        assert result[1].agent_id == "agent-2"
        assert result[1].total_executions == 10


class TestBuildLLMMessages:
    """Test _build_llm_messages private method"""

    async def test_includes_system_message(self, service, mock_conversation_repo, test_user_id):
        """Test that system message is always included"""
        # Arrange
        mock_conversation_repo.get_messages.return_value = []

        # Act
        messages = await service._build_llm_messages("conv-123")

        # Assert
        assert len(messages) > 0
        assert "AI assistant" in messages[0].content

    async def test_includes_conversation_history(self, service, mock_conversation_repo, test_user_id):
        """Test that conversation history is included"""
        # Arrange
        msg1 = Mock(spec=Message)
        msg1.role = "user"
        msg1.content = "Hello"

        msg2 = Mock(spec=Message)
        msg2.role = "assistant"
        msg2.content = "Hi there!"

        mock_conversation_repo.get_messages.return_value = [msg1, msg2]

        # Act
        messages = await service._build_llm_messages("conv-123")

        # Assert
        assert len(messages) == 3  # System + 2 history
        assert messages[1].content == "Hello"
        assert messages[2].content == "Hi there!"
