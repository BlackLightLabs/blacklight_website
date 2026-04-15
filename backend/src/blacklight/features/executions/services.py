"""
Agent execution service for running created agents

Handles the execution of created agents, manages the execution
lifecycle, tracks costs, and updates execution records.
"""

from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.blacklight.features.agents.models import AgentStatusEnum
from src.blacklight.features.agents.repositories import AgentRepository
from src.blacklight.features.executions.models import ExecutionStatusEnum
from src.blacklight.features.executions.repositories import ExecutionRepository


class AgentState(TypedDict):
    """State for agent execution"""

    messages: list[str]
    current_step: str
    data: dict[str, Any]


class AgentExecutionService:
    """
    Service for executing AI agents.

    This service manages the execution of created agents, tracking their
    progress, costs, and results through the execution repository.

    Uses dependency injection - repositories are provided via constructor.
    """

    def __init__(
        self, agent_repository: AgentRepository, execution_repository: ExecutionRepository
    ):
        """
        Initialize the service with repository dependencies.

        Args:
            agent_repository: Repository for agent data operations
            execution_repository: Repository for execution tracking
        """
        self.agent_repo = agent_repository
        self.execution_repo = execution_repository

    async def execute_agent(
        self, agent_id: str, input_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute a created agent.

        Args:
            agent_id: ID of the agent to execute
            input_data: Input data for the agent

        Returns:
            Dictionary with execution results

        Raises:
            ValueError: If agent not found or not ready
        """
        # Get agent from database
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if agent.status != AgentStatusEnum.READY:
            raise ValueError(f"Agent {agent_id} is not ready (status: {agent.status})")

        # Create execution record
        execution = await self.execution_repo.create_execution(
            agent_id=agent_id, input_data=input_data
        )

        try:
            # Update execution status to running
            await self.execution_repo.update_status(execution.id, ExecutionStatusEnum.RUNNING)

            # Build and execute the agent graph
            result = await self._execute_agent_graph(agent, input_data)

            # Calculate cost
            execution_cost = agent.estimated_cost_per_run

            # Update execution with results
            await self.execution_repo.update_status(
                execution.id, ExecutionStatusEnum.COMPLETED, output_data=result
            )
            await self.execution_repo.set_cost(execution.id, execution_cost)

            # Update agent metrics
            await self.agent_repo.increment_executions(agent_id, execution_cost)

            return {
                "status": "completed",
                "result": result,
                "cost": execution_cost,
                "execution_id": execution.id,
            }

        except Exception as e:
            # Update execution with error
            await self.execution_repo.update_status(
                execution.id, ExecutionStatusEnum.FAILED, error_message=str(e)
            )
            raise

    async def _execute_agent_graph(
        self, agent, input_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Execute the agent's LangGraph workflow.

        Args:
            agent: Agent database model
            input_data: Input data for execution

        Returns:
            Execution result
        """
        # Rebuild the graph from the agent spec
        spec = agent.spec

        workflow = StateGraph(AgentState)

        # Add nodes for each step
        for i, step in enumerate(spec.get("steps", [])):
            node_name = f"step_{i}"
            workflow.add_node(node_name, self._create_step_function(step))

        # Set entry point
        if spec.get("steps"):
            workflow.set_entry_point("step_0")

            # Chain steps together
            for i in range(len(spec["steps"]) - 1):
                workflow.add_edge(f"step_{i}", f"step_{i+1}")

            # Last step goes to END
            workflow.add_edge(f"step_{len(spec['steps'])-1}", END)

        # Compile and execute
        compiled_graph = workflow.compile()

        initial_state: AgentState = {"messages": [], "current_step": "", "data": input_data or {}}

        result = await compiled_graph.ainvoke(initial_state)

        return result

    def _create_step_function(self, step_description: str):
        """
        Create a function for a graph node based on step description.

        Args:
            step_description: Description of the step

        Returns:
            Step function for the graph node
        """

        def step_fn(state: AgentState) -> AgentState:
            # This is a simplified version - in production, this would use LLM
            # to actually execute the step based on the description
            state["messages"].append(f"Executing: {step_description}")
            state["current_step"] = step_description
            return state

        return step_fn

    async def get_execution(self, execution_id: str):
        """
        Get execution details.

        Args:
            execution_id: The execution ID

        Returns:
            Execution database model or None
        """
        return await self.execution_repo.get_by_id(execution_id)

    async def get_agent_executions(self, agent_id: str, limit: int = 100):
        """
        Get execution history for an agent.

        Args:
            agent_id: The agent ID
            limit: Maximum number of executions to return

        Returns:
            List of execution records
        """
        return await self.execution_repo.get_by_agent_id(agent_id, limit)
