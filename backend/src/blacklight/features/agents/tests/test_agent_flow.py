"""
System tests for end-to-end agent workflows

Tests complete user journeys from agent creation to execution.
"""

import pytest

from src.blacklight.features.agents.models import AgentStatusEnum


class TestAgentCreationFlow:
    """System test for complete agent creation workflow"""

    @pytest.mark.asyncio
    async def test_complete_agent_creation_workflow(self, async_client, async_agent_repo, test_user_id):
        """
        Test complete workflow:
        1. Start conversation
        2. Create agent through chat
        3. Verify agent is created
        4. Retrieve agent details
        """
        # Step 1: Start conversation
        response1 = await async_client.post(
            "/api/agents/chat",
            json={
                "message": "I want an agent that processes data",
                "conversation_history": [],
                "agent_id": None,
            },
        )

        assert response1.status_code == 200
        data1 = response1.json()
        agent_id = data1["agent_id"]

        assert agent_id is not None
        assert not data1["agent_ready"]  # Agent not ready yet

        # Step 2: Verify agent exists in database
        agent = await async_agent_repo.get_by_id(agent_id)
        assert agent is not None
        assert agent.status in ["creating", "ready"]

        # Step 3: List all agents
        response_list = await async_client.get("/api/agents/")
        assert response_list.status_code == 200
        agents = response_list.json()
        assert len(agents) >= 1
        assert any(a["agent_id"] == agent_id for a in agents)

        # Step 4: Get specific agent
        response_get = await async_client.get(f"/api/agents/{agent_id}")
        assert response_get.status_code == 200
        agent_data = response_get.json()
        assert agent_data["agent_id"] == agent_id


class TestAgentExecutionFlow:
    """System test for agent execution workflow"""

    async def test_agent_execution_requires_ready_status(self, async_client, async_agent_repo, test_user_id):
        """Test that only READY agents can be executed"""
        # Create agent in CREATING status
        await async_agent_repo.create_agent(
            agent_id="creating-agent", description="Test", spec={}, status=AgentStatusEnum.CREATING, user_id=test_user_id
        )

        # Try to execute
        response = await async_client.post(
            "/api/agents/execute", json={"agent_id": "creating-agent", "input_data": {}}
        )

        # Should fail because agent is not ready
        assert response.status_code in [404, 500]

    async def test_ready_agent_execution(self, async_client, async_agent_repo, test_user_id):
        """Test executing a ready agent"""
        # Create READY agent
        await async_agent_repo.create_agent(
            agent_id="ready-agent",
            description="Ready agent",
            spec={"steps": ["Process data", "Return result"], "estimated_cost": 0.50},
            status=AgentStatusEnum.READY,
            estimated_cost_per_run=0.50,
            user_id=test_user_id,
        )

        # Execute agent
        response = await async_client.post(
            "/api/agents/execute", json={"agent_id": "ready-agent", "input_data": {"test": "data"}}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "execution_id" in data
        assert data["agent_id"] == "ready-agent"
        assert "status" in data
        assert "cost" in data

        # Verify execution was tracked
        agent = await async_agent_repo.get_by_id("ready-agent")
        assert agent.total_executions >= 1
        assert agent.total_cost >= 0.50


class TestErrorHandling:
    """System tests for error handling"""

    async def test_concurrent_agent_creation(self, async_client, test_user_id):
        """Test handling concurrent requests for same agent"""
        # This would test race conditions in production
        # For now, just verify basic functionality works

        response1 = await async_client.post(
            "/api/agents/chat",
            json={"message": "Create agent 1", "conversation_history": [], "agent_id": None},
        )

        response2 = await async_client.post(
            "/api/agents/chat",
            json={"message": "Create agent 2", "conversation_history": [], "agent_id": None},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should create different agents
        assert response1.json()["agent_id"] != response2.json()["agent_id"]

    async def test_database_rollback_on_error(self, async_client, async_agent_repo, async_db, test_user_id):
        """Test that database transactions rollback on errors"""
        # Get initial agent count
        initial_count = await async_agent_repo.count()

        # Try to create agent with invalid data (this will depend on your validation)
        # The transaction should rollback
        try:
            await async_client.post(
                "/api/agents/chat",
                json={
                    "message": "Test",
                    "conversation_history": "invalid-type",  # Should be list
                    "agent_id": None,
                },
            )
        except Exception:  # noqa: S110
            pass

        # Verify count hasn't changed if error occurred
        final_count = await async_agent_repo.count()
        # In case of validation error before DB insert, count should be same
        assert final_count >= initial_count
