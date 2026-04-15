"""
Agents feature dependencies for FastAPI dependency injection

Provides service and repository dependencies for agent creation and management routes.
"""

from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.database import get_db
from src.blacklight.features.agents.build_pipeline import BuildPipeline
from src.blacklight.features.agents.error_analyzer import ErrorAnalyzer
from src.blacklight.features.agents.mcp_service import MCPService
from src.blacklight.features.agents.prompt_service import PromptService
from src.blacklight.features.agents.repositories import (
    AgentRepository,
    AgentVersionRepository,
    AgentBuildLogRepository,
    AgentTestRunRepository,
    ConversationRepository,
)
from src.blacklight.features.agents.services import AgentBuilderService
from src.blacklight.features.agents.spec_reviser import SpecReviser


# Repository dependencies

def get_agent_repository(db: AsyncSession = Depends(get_db)) -> AgentRepository:
    """
    Get agent repository dependency

    Args:
        db: Async database session

    Returns:
        AgentRepository instance
    """
    return AgentRepository(db)


def get_conversation_repository(db: AsyncSession = Depends(get_db)) -> ConversationRepository:
    """
    Get conversation repository dependency

    Args:
        db: Async database session

    Returns:
        ConversationRepository instance
    """
    return ConversationRepository(db)


def get_version_repository(db: AsyncSession = Depends(get_db)) -> AgentVersionRepository:
    """
    Get agent version repository dependency

    Args:
        db: Async database session

    Returns:
        AgentVersionRepository instance
    """
    return AgentVersionRepository(db)


def get_build_log_repository(db: AsyncSession = Depends(get_db)) -> AgentBuildLogRepository:
    """
    Get build log repository dependency

    Args:
        db: Async database session

    Returns:
        AgentBuildLogRepository instance
    """
    return AgentBuildLogRepository(db)


def get_test_run_repository(db: AsyncSession = Depends(get_db)) -> AgentTestRunRepository:
    """
    Get test run repository dependency

    Args:
        db: Async database session

    Returns:
        AgentTestRunRepository instance
    """
    return AgentTestRunRepository(db)


def get_prompt_service(db: AsyncSession = Depends(get_db)) -> PromptService:
    """
    Get prompt service dependency

    Args:
        db: Async database session

    Returns:
        PromptService instance
    """
    return PromptService(db)


def get_mcp_service(db: AsyncSession = Depends(get_db)) -> MCPService:
    """
    Get MCP service dependency

    Args:
        db: Async database session

    Returns:
        MCPService instance
    """
    return MCPService(db)


def get_error_analyzer() -> ErrorAnalyzer:
    """
    Get error analyzer dependency

    Returns:
        ErrorAnalyzer instance
    """
    return ErrorAnalyzer()


def get_spec_reviser(
    prompt_service: PromptService = Depends(get_prompt_service),
    error_analyzer: ErrorAnalyzer = Depends(get_error_analyzer),
) -> SpecReviser:
    """
    Get spec reviser dependency

    Args:
        prompt_service: Prompt service (injected by FastAPI)
        error_analyzer: Error analyzer (injected by FastAPI)

    Returns:
        SpecReviser instance
    """
    return SpecReviser(prompt_service, error_analyzer)


# Service dependencies

def get_build_pipeline(
    version_repo: AgentVersionRepository = Depends(get_version_repository),
    log_repo: AgentBuildLogRepository = Depends(get_build_log_repository),
    test_run_repo: AgentTestRunRepository = Depends(get_test_run_repository),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    error_analyzer: ErrorAnalyzer = Depends(get_error_analyzer),
    spec_reviser: SpecReviser = Depends(get_spec_reviser),
) -> BuildPipeline:
    """
    Get build pipeline dependency

    Args:
        version_repo: Version repository (injected by FastAPI)
        log_repo: Build log repository (injected by FastAPI)
        test_run_repo: Test run repository (injected by FastAPI)
        agent_repo: Agent repository (injected by FastAPI)
        error_analyzer: Error analyzer (injected by FastAPI)
        spec_reviser: Spec reviser (injected by FastAPI)

    Returns:
        BuildPipeline instance with self-repair enabled
    """
    # Get sandbox root from environment or use default
    import os
    sandbox_root = Path(os.getenv("AGENT_SANDBOX_ROOT", "./backend/generated"))

    # Get max retries from environment
    max_retries = int(os.getenv("MAX_BUILD_RETRIES", "3"))

    return BuildPipeline(
        version_repo=version_repo,
        log_repo=log_repo,
        test_run_repo=test_run_repo,
        agent_repo=agent_repo,
        sandbox_root=sandbox_root,
        error_analyzer=error_analyzer,
        spec_reviser=spec_reviser,
        max_retries=max_retries,
    )


def get_agent_builder_service(
    agent_repo: AgentRepository = Depends(get_agent_repository),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
    build_pipeline: BuildPipeline = Depends(get_build_pipeline),
    mcp_service: MCPService = Depends(get_mcp_service),
) -> AgentBuilderService:
    """
    Get agent builder service dependency

    Provides AgentBuilderService with injected repositories, prompt service, build pipeline,
    and MCP service for tool discovery.

    Args:
        agent_repo: Agent repository (injected by FastAPI)
        conversation_repo: Conversation repository (injected by FastAPI)
        prompt_service: Prompt service (injected by FastAPI)
        build_pipeline: Build pipeline (injected by FastAPI)
        mcp_service: MCP service (injected by FastAPI)

    Returns:
        AgentBuilderService instance
    """
    return AgentBuilderService(
        agent_repository=agent_repo,
        conversation_repository=conversation_repo,
        prompt_service=prompt_service,
        build_pipeline=build_pipeline,
        mcp_service=mcp_service,
    )
