"""
Agent Creation and Build System

This feature module handles the conversational agent creation process,
including the multi-phase build pipeline that generates LangGraph agents
from natural language descriptions.

Components:
    - AgentBuilderService: Conversational agent creation with streaming
    - BuildPipeline: Multi-phase agent build system
    - MCPService: Model Context Protocol server integration
    - AgentRepository: Agent data persistence
    - ConversationRepository: Chat history persistence

Build Pipeline Phases:
    1. Planning: Generate agent specification from conversation
    2. Code Generation: Create Python code for the agent
    3. Validation: Static analysis and linting
    4. Testing: Generate and run verification tests
    5. Packaging: Bundle agent for execution

Key Features:
    - Real-time streaming responses via SSE
    - Automatic agent versioning
    - Build error recovery and self-repair
    - Comprehensive build logging
    - MCP server tool integration

Database Models:
    - Agent: Agent metadata and current status
    - AgentVersion: Version history and build artifacts
    - AgentBuildLog: Detailed build phase logs
    - Conversation: Chat sessions between user and AI
    - Message: Individual chat messages
    - MCPServer: MCP server configurations
    - AgentMCPBinding: Agent-to-MCP-server relationships
    - MCPToolExecution: Tool execution history

Usage Example:
    ```python
    from src.blacklight.features.agents.dependencies import get_agent_builder_service

    # In a route handler
    async def create_agent(
        service: AgentBuilderService = Depends(get_agent_builder_service)
    ):
        conversation = await service.create_conversation(user_id=user_id)
        async for chunk in service.stream_response(conversation.id, message):
            yield chunk
    ```

For detailed architecture documentation, see backend/AGENT_ARCHITECTURE.md.
"""
