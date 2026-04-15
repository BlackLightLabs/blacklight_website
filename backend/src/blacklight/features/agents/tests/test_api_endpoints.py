"""
Integration tests for API endpoints

Tests the complete API flow with database interactions.
"""

from src.blacklight.features.agents.models import AgentStatusEnum


class TestAgentEndpoints:
    """Integration tests for agent API endpoints"""

    async def test_list_agents_empty(self, async_client, test_user_id):
        """Test listing agents when none exist"""
        response = await async_client.get("/api/agents/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_nonexistent_agent(self, async_client, test_user_id):
        """Test getting non-existent agent returns 404"""
        response = await async_client.get("/api/agents/nonexistent-id")

        assert response.status_code == 404

    async def test_chat_creates_agent(self, async_client, test_user_id):
        """Test chat endpoint creates agent"""
        response = await async_client.post(
            "/api/agents/chat",
            json={"message": "I want a test agent", "conversation_history": [], "agent_id": None},
        )

        assert response.status_code == 200
        data = response.json()

        assert "agent_id" in data
        assert "message" in data
        assert "agent_ready" in data
        assert isinstance(data["agent_ready"], bool)

    async def test_chat_continues_conversation(self, async_client, test_user_id):
        """Test continuing a conversation with existing agent"""
        # First message
        response1 = await async_client.post(
            "/api/agents/chat",
            json={"message": "I want a test agent", "conversation_history": [], "agent_id": None},
        )
        agent_id = response1.json()["agent_id"]

        # Continue conversation
        response2 = await async_client.post(
            "/api/agents/chat",
            json={
                "message": "Make it do X",
                "conversation_history": [
                    {"role": "user", "content": "I want a test agent"},
                    {"role": "assistant", "content": "Sure, tell me more"},
                ],
                "agent_id": agent_id,
            },
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["agent_id"] == agent_id

    async def test_execute_nonexistent_agent(self, async_client, test_user_id):
        """Test executing non-existent agent returns 404"""
        response = await async_client.post(
            "/api/agents/execute", json={"agent_id": "nonexistent", "input_data": {}}
        )

        assert response.status_code == 404

    async def test_health_endpoint(self, async_client, test_user_id):
        """Test health check endpoint"""
        response = await async_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_root_endpoint(self, async_client, test_user_id):
        """Test root endpoint"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data


class TestChatValidation:
    """Tests for chat endpoint input validation"""

    async def test_chat_with_empty_message(self, async_client, test_user_id):
        """Test chat with empty message"""
        response = await async_client.post(
            "/api/agents/chat", json={"message": "", "conversation_history": [], "agent_id": None}
        )

        # Should still work, but might return specific response
        assert response.status_code in [200, 422]

    async def test_chat_with_invalid_agent_id(self, async_client, test_user_id):
        """Test chat with invalid agent ID format"""
        response = await async_client.post(
            "/api/agents/chat",
            json={
                "message": "Test",
                "conversation_history": [],
                "agent_id": "invalid-id-that-does-not-exist",
            },
        )

        # Should handle gracefully
        assert response.status_code in [200, 404, 500]

    async def test_chat_with_null_conversation_history(self, async_client, test_user_id):
        """Test chat with null conversation history"""
        response = await async_client.post(
            "/api/agents/chat",
            json={"message": "Test", "conversation_history": None, "agent_id": None},
        )

        # Pydantic should handle default
        assert response.status_code == 200


class TestExecutionValidation:
    """Tests for execution endpoint validation"""

    async def test_execute_with_missing_agent_id(self, async_client, test_user_id):
        """Test execution without agent_id"""
        response = await async_client.post("/api/agents/execute", json={"input_data": {}})

        assert response.status_code == 422  # Validation error

    async def test_execute_with_invalid_input_data(self, async_client, async_agent_repo, test_user_id):
        """Test execution with invalid input data types"""
        # Create a ready agent first
        await async_agent_repo.create_agent(
            agent_id="test-ready", description="Test", spec={"steps": []}, status=AgentStatusEnum.READY, user_id=test_user_id
        )

        response = await async_client.post(
            "/api/agents/execute",
            json={"agent_id": "test-ready", "input_data": "not-a-dict"},  # Should be dict
        )

        assert response.status_code == 422  # Validation error
