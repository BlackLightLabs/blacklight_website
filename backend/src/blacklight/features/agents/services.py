"""
Agent Builder Service

This service handles the conversational agent creation flow where users
chat with an AI to design custom agents. It uses repositories for data persistence
and LangChain/LangGraph for LLM interactions and agent workflows.

Key features:
- Conversational agent design interface
- Real-time token streaming via SSE
- Multi-provider LLM support (OpenAI, xAI Grok, local LMStudio)
- Database-backed persistence with SQLAlchemy repositories
- User-scoped agent access control

Architecture:
- Uses LangChain for LLM interactions
- Uses LangGraph for agent workflow construction
- Uses Repository pattern for database operations
- Supports async/await for better performance
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.blacklight.common.llm_config import LLMConfig
from src.blacklight.features.agents.models import AgentStatusEnum, PromptTemplateType
from src.blacklight.features.agents.mcp_service import MCPService
from src.blacklight.features.agents.prompt_service import PromptService
from src.blacklight.features.agents.repositories import (
    AgentRepository,
    ConversationRepository,
)
from src.blacklight.features.agents.schemas import AgentDetails, ChatMessage


class StreamingCallbackHandler(AsyncCallbackHandler):
    """
    Custom callback handler for streaming LLM tokens in real-time

    Uses asyncio.Queue to buffer tokens as they're generated and provides
    an async iterator interface for consuming them via Server-Sent Events.
    """

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.done = False

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated"""
        await self.queue.put(token)

    async def on_llm_end(self, *args, **kwargs) -> None:
        """Called when LLM finishes"""
        self.done = True

    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM encounters an error"""
        self.done = True
        await self.queue.put(None)  # Signal error

    async def aiter(self) -> AsyncIterator[str]:
        """Async iterator for tokens"""
        while not self.done or not self.queue.empty():
            try:
                token = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                if token is None:  # Error signal
                    break
                yield token
            except asyncio.TimeoutError:
                continue


class AgentState(TypedDict):
    """State for a dynamically created agent"""

    messages: list[str]
    current_step: str
    data: dict[str, Any]


class AgentBuilderService:
    """
    Service for building and managing AI agents through conversation.

    This service handles the conversational agent creation flow where users
    describe what they want and the LLM helps design custom agents.

    Uses dependency injection - repositories are provided via constructor.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        conversation_repository: ConversationRepository,
        prompt_service: PromptService,
        build_pipeline: Any = None,  # BuildPipeline - Any to avoid circular import
        mcp_service: MCPService | None = None,
    ):
        """
        Initialize the service with repository dependencies.

        Args:
            agent_repository: Repository for agent data operations
            conversation_repository: Repository for conversation operations
            prompt_service: Service for loading and rendering prompt templates
            build_pipeline: Build pipeline for compiling and testing agents
            mcp_service: MCP service for tool discovery and suggestions
        """
        self.agent_repo = agent_repository
        self.conversation_repo = conversation_repository
        self.prompt_service = prompt_service
        self.build_pipeline = build_pipeline
        self.mcp_service = mcp_service
        self.llm = LLMConfig.get_llm()

    async def chat_for_agent_creation(
        self,
        message: str,
        user_id: int,
        conversation_history: list[ChatMessage] | None = None,
        agent_id: str | None = None,
    ) -> tuple[str, str, bool, AgentDetails | None]:
        """
        Chat with user to understand their agent requirements.

        Args:
            message: User's message
            user_id: ID of the user creating the agent
            conversation_history: Previous conversation messages
            agent_id: Existing agent ID if continuing conversation

        Returns:
            (agent_id, response_message, agent_ready, agent_details)
        """
        # Create or retrieve agent and conversation
        if agent_id is None:
            agent_id = str(uuid.uuid4())
            # Create agent in CREATING status
            await self.agent_repo.create_agent(
                agent_id=agent_id,
                description="Agent being created",
                spec={},
                user_id=user_id,
                status=AgentStatusEnum.CREATING,
            )

        # Get or create conversation
        conversation = await self.conversation_repo.get_or_create_conversation(
            agent_id=agent_id, user_id=user_id, conversation_id=None
        )

        # Add user message to conversation
        await self.conversation_repo.add_message(
            conversation_id=conversation.id, role="user", content=message
        )

        # Build conversation for LLM
        messages = await self._build_llm_messages(conversation.id)

        # Get LLM response
        response = await self.llm.ainvoke(messages)
        response_text = response.content

        # Add assistant response to conversation
        await self.conversation_repo.add_message(
            conversation_id=conversation.id, role="assistant", content=response_text
        )

        # Check if agent is ready
        agent_ready = False
        agent_details = None

        if "AGENT_READY:" in response_text:
            agent_ready = True
            # Extract JSON from response
            try:
                json_start = response_text.index("{")
                json_end = response_text.rindex("}") + 1
                agent_spec = json.loads(response_text[json_start:json_end])

                # Create the agent from specification
                agent_details = await self._create_agent_from_spec(agent_id, agent_spec)

                # Clean up response text to remove JSON
                response_text = response_text[: response_text.index("AGENT_READY:")].strip()
                if not response_text:
                    response_text = "Great! Your agent has been created and is ready to use."

            except (ValueError, json.JSONDecodeError):
                agent_ready = False
                response_text = "I encountered an error creating your agent. Let's try again."

        return agent_id, response_text, agent_ready, agent_details

    async def chat_for_agent_creation_stream(
        self,
        message: str,
        user_id: int,
        conversation_history: list[ChatMessage] | None = None,
        agent_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream chat responses for agent creation.

        Yields SSE events with types:
        - token: Individual text chunks (filtered of technical JSON)
        - thinking: AI thinking/analyzing messages
        - graph_update: Incremental graph structure updates
        - build_started: Build pipeline initiated
        - build_progress: Build progress updates (stage, percentage)
        - mcp_suggestions: Suggested MCP servers based on user requirements
        - agent_ready: Agent creation complete
        - agent_details: Agent specification
        - done: Stream complete

        Args:
            message: User's message
            user_id: ID of the user creating the agent
            conversation_history: Previous conversation messages
            agent_id: Existing agent ID if continuing conversation

        Yields:
            Event dictionaries for SSE stream
        """
        # Create or retrieve agent and conversation
        if agent_id is None:
            agent_id = str(uuid.uuid4())
            # Create agent in CREATING status
            await self.agent_repo.create_agent(
                agent_id=agent_id,
                description="Agent being created",
                spec={},
                user_id=user_id,
                status=AgentStatusEnum.CREATING,
            )
            yield {"type": "agent_id", "agent_id": agent_id}

        # Generate MCP server suggestions based on user's message
        if self.mcp_service and len(message) > 10:  # Only for substantial messages
            try:
                suggestions = await self.mcp_service.suggest_mcp_servers(message)
                if suggestions:
                    # Filter to only available servers
                    available_suggestions = [s for s in suggestions if s["available"]]
                    if available_suggestions:
                        yield {
                            "type": "mcp_suggestions",
                            "suggestions": available_suggestions,
                        }
            except Exception as e:
                # Don't fail chat if suggestions fail
                import structlog
                logger = structlog.get_logger(__name__)
                logger.warning("mcp_suggestions_failed", error=str(e))

        # Get or create conversation
        conversation = await self.conversation_repo.get_or_create_conversation(
            agent_id=agent_id, user_id=user_id, conversation_id=None
        )

        # Add user message to conversation
        await self.conversation_repo.add_message(
            conversation_id=conversation.id, role="user", content=message
        )

        # Build conversation for LLM
        messages = await self._build_llm_messages(conversation.id)

        # Create streaming callback handler
        callback = StreamingCallbackHandler()

        # Create streaming LLM
        streaming_llm = LLMConfig.get_llm(streaming=True, callbacks=[callback])

        # Start streaming task
        task = asyncio.create_task(streaming_llm.ainvoke(messages))

        # Accumulate response for saving to history
        accumulated_response = ""
        # Track if we're inside AGENT_READY JSON block
        inside_agent_ready = False

        try:
            # Stream tokens as they arrive, filtering out AGENT_READY JSON
            async for token in callback.aiter():
                accumulated_response += token

                # Check if we're entering AGENT_READY block
                if "AGENT_READY:" in accumulated_response and not inside_agent_ready:
                    inside_agent_ready = True
                    # Send thinking message before suppressing JSON
                    yield {"type": "thinking", "message": "Building your agent..."}
                    continue

                # If we're inside AGENT_READY block, don't stream tokens
                if inside_agent_ready:
                    # Check if JSON block is complete (rough heuristic)
                    if token == "}" and accumulated_response.count("{") <= accumulated_response.count("}"):
                        inside_agent_ready = False
                    continue

                # Stream normal conversational tokens
                yield {"type": "token", "content": token}

            # Wait for task to complete
            await task

            # Add assistant response to conversation (with JSON for history)
            await self.conversation_repo.add_message(
                conversation_id=conversation.id, role="assistant", content=accumulated_response
            )

            # Check if agent is ready
            if "AGENT_READY:" in accumulated_response:
                try:
                    json_start = accumulated_response.index("{")
                    json_end = accumulated_response.rindex("}") + 1
                    agent_spec = json.loads(accumulated_response[json_start:json_end])

                    # Stream graph structure for visualization
                    yield {"type": "graph_update", "graph": {
                        "nodes": agent_spec.get("nodes", []),
                        "edges": agent_spec.get("edges", []),
                    }}

                    # Signal build starting
                    yield {"type": "build_started", "agent_id": agent_id}

                    # Create the agent (with build pipeline)
                    agent_details = await self._create_agent_from_spec(agent_id, agent_spec)

                    yield {"type": "agent_ready", "agent_id": agent_id}
                    yield {"type": "agent_details", "details": agent_details.model_dump(mode='json')}

                except (ValueError, json.JSONDecodeError) as e:
                    yield {"type": "error", "message": f"Error creating agent from specification: {e}"}

            # Signal completion
            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}

    async def _create_agent_from_spec(self, agent_id: str, spec: dict[str, Any]) -> AgentDetails:
        """
        Create a LangGraph agent from a specification using BuildPipeline.

        Args:
            agent_id: The agent ID
            spec: Agent specification dictionary

        Returns:
            AgentDetails model
        """
        # Validate spec against AgentSpec schema
        from pydantic import ValidationError
        from src.blacklight.features.agents.spec_schema import AgentSpec

        try:
            validated_spec = AgentSpec(**spec)
        except ValidationError as e:
            # Log validation errors
            error_msg = f"Spec validation failed: {e}"
            await self.agent_repo.update(
                agent_id,
                status=AgentStatusEnum.FAILED,
                spec=spec,  # Store invalid spec for debugging
            )
            raise ValueError(error_msg) from e

        # Trigger build pipeline if available
        if self.build_pipeline:
            try:
                # Run build pipeline (generates code, runs tests)
                version = await self.build_pipeline.run(agent_id, validated_spec)

                # Get updated agent
                agent = await self.agent_repo.get_by_id(agent_id)

                return AgentDetails(
                    agent_id=agent_id,
                    status=agent.status,
                    description=validated_spec.description,
                    created_at=agent.created_at,
                    graph_structure=spec,
                    estimated_cost_per_run=validated_spec.runtime.budget_usd,
                    total_executions=agent.total_executions,
                    total_cost=agent.total_cost,
                )

            except Exception as e:
                # Build pipeline failed, update agent status
                await self.agent_repo.update(
                    agent_id,
                    status=AgentStatusEnum.FAILED,
                    spec=spec,
                )
                raise ValueError(f"Build pipeline failed: {e}") from e
        else:
            # Fallback: No build pipeline, just update agent with spec
            # (For backwards compatibility during development)
            agent = await self.agent_repo.update(
                agent_id,
                status=AgentStatusEnum.READY,
                description=validated_spec.description,
                spec=spec,
                estimated_cost_per_run=validated_spec.runtime.budget_usd,
            )

            return AgentDetails(
                agent_id=agent_id,
                status=AgentStatusEnum.READY,
                description=validated_spec.description,
                created_at=agent.created_at,
                graph_structure=spec,
                estimated_cost_per_run=validated_spec.runtime.budget_usd,
                total_executions=agent.total_executions,
                total_cost=agent.total_cost,
            )

    def _create_step_function(self, step_description: str):
        """Create a function for a graph node based on step description"""

        def step_fn(state: AgentState) -> AgentState:
            # This is a simplified version - in production, this would use LLM
            # to actually execute the step
            state["messages"].append(f"Executing: {step_description}")
            state["current_step"] = step_description
            return state

        return step_fn

    async def _build_llm_messages(self, conversation_id: str) -> list:
        """
        Build LLM message list from conversation history.

        Includes:
        - System prompt with tool catalog (local + MCP tools)
        - MCP server suggestions based on conversation context
        - Conversation history

        Args:
            conversation_id: The conversation ID

        Returns:
            List of LangChain messages
        """
        # Get tool catalog for system prompt
        from src.blacklight.features.agents.tools.registry import get_tool_registry
        from src.blacklight.features.agents.spec_schema import EXAMPLE_SUPPORT_AGENT

        tool_catalog = get_tool_registry().get_catalog_text()
        example_spec = json.dumps(EXAMPLE_SUPPORT_AGENT, indent=2)

        # Get MCP tool catalog if MCP service is available
        mcp_catalog = ""
        if self.mcp_service:
            try:
                mcp_catalog = await self.mcp_service.get_mcp_tool_catalog_for_prompt()
            except Exception as e:
                # Don't fail agent creation if MCP catalog fails
                import structlog
                logger = structlog.get_logger(__name__)
                logger.warning("mcp_catalog_generation_failed", error=str(e))
                mcp_catalog = ""

        # Render system prompt from database template
        system_prompt = await self.prompt_service.render_template(
            name="agent_creation_system",
            variables={
                "tool_catalog": tool_catalog,
                "mcp_catalog": mcp_catalog,
                "example_spec": example_spec,
            },
            template_type=PromptTemplateType.SYSTEM,
        )

        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history from database
        conv_messages = await self.conversation_repo.get_messages(conversation_id)
        for msg in conv_messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        return messages

    async def get_agent(
        self, agent_id: str, user_id: int, is_superuser: bool = False
    ) -> AgentDetails | None:
        """
        Get agent details.

        Args:
            agent_id: The agent ID
            user_id: The user ID
            is_superuser: Whether the user is a superuser (can see all agents)

        Returns:
            AgentDetails or None if not found or unauthorized
        """
        # Superusers can see all agents
        if is_superuser:
            agent = await self.agent_repo.get_by_id(agent_id)
        else:
            # Regular users can only see their own agents
            agent = await self.agent_repo.get_by_id_and_user(agent_id, user_id)

        if not agent:
            return None

        return AgentDetails(
            agent_id=agent.id,
            status=agent.status,
            description=agent.description,
            created_at=agent.created_at,
            graph_structure=agent.spec,
            estimated_cost_per_run=agent.estimated_cost_per_run,
            total_executions=agent.total_executions,
            total_cost=agent.total_cost,
        )

    async def list_agents(self, user_id: int, is_superuser: bool = False) -> list[AgentDetails]:
        """
        List agents for a user.

        Args:
            user_id: The user ID
            is_superuser: Whether the user is a superuser (can see all agents)

        Returns:
            List of AgentDetails
        """
        # Superusers can see all agents
        if is_superuser:
            agents = await self.agent_repo.get_all()
        else:
            # Regular users can only see their own agents
            agents = await self.agent_repo.get_by_user_id(user_id)

        return [
            AgentDetails(
                agent_id=agent.id,
                status=agent.status,
                description=agent.description,
                created_at=agent.created_at,
                graph_structure=agent.spec,
                estimated_cost_per_run=agent.estimated_cost_per_run,
                total_executions=agent.total_executions,
                total_cost=agent.total_cost,
            )
            for agent in agents
        ]
