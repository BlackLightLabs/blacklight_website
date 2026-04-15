"""
Executions feature dependencies for FastAPI dependency injection

Provides service and repository dependencies for agent execution routes.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.database import get_db
from src.blacklight.features.agents.repositories import AgentRepository
from src.blacklight.features.executions.repositories import ExecutionRepository
from src.blacklight.features.executions.services import AgentExecutionService


def get_execution_repository(db: AsyncSession = Depends(get_db)) -> ExecutionRepository:
    """
    Get execution repository dependency

    Args:
        db: Async database session

    Returns:
        ExecutionRepository instance
    """
    return ExecutionRepository(db)


def get_agent_execution_service(
    db: AsyncSession = Depends(get_db),
) -> AgentExecutionService:
    """
    Get agent execution service dependency

    Provides AgentExecutionService with injected repositories.

    Args:
        db: Async database session

    Returns:
        AgentExecutionService instance
    """
    agent_repo = AgentRepository(db)
    execution_repo = ExecutionRepository(db)
    return AgentExecutionService(agent_repository=agent_repo, execution_repository=execution_repo)
