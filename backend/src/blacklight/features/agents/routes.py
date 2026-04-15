"""
Agent routes for creation, listing, and execution

Provides HTTP endpoints for:
- Chat-based agent creation (streaming and non-streaming)
- Listing and retrieving agents
- Agent execution
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.blacklight.common.exceptions import AgentNotFoundError
from src.blacklight.dependencies.permissions import RequirePermission
from src.blacklight.features.agents import dependencies, repositories, schemas
from src.blacklight.features.agents.build_pipeline import BuildPipeline
from src.blacklight.features.agents.dependencies import get_agent_builder_service
from src.blacklight.features.agents.schemas import (
    AgentDetails,
    ChatRequest,
    ChatResponse,
)
from src.blacklight.features.agents.services import AgentBuilderService
from src.blacklight.features.auth.models import User
from src.blacklight.features.executions.dependencies import (
    get_agent_execution_service,
)
from src.blacklight.features.executions.schemas import (
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from src.blacklight.features.executions.services import AgentExecutionService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_for_agent_creation(
    request: ChatRequest,
    user: User = Depends(RequirePermission("agents:create")),
    service: AgentBuilderService = Depends(get_agent_builder_service),
):
    """
    Chat endpoint for creating agents through conversation.
    Users describe what they want and the LLM helps design the agent.

    Requires: agents:create permission

    Note: Exceptions are handled by global exception handlers.
    """
    agent_id, response_message, agent_ready, agent_details = (
        await service.chat_for_agent_creation(
            message=request.message,
            user_id=user.id,
            conversation_history=request.conversation_history,
            agent_id=request.agent_id,
        )
    )

    return ChatResponse(
        agent_id=agent_id,
        message=response_message,
        agent_ready=agent_ready,
        agent_details=agent_details,
    )


@router.post("/chat/stream")
async def chat_for_agent_creation_stream(
    request: ChatRequest,
    user: User = Depends(RequirePermission("agents:create")),
    service: AgentBuilderService = Depends(get_agent_builder_service),
):
    """
    Streaming endpoint for creating agents through conversation.
    Returns Server-Sent Events (SSE) stream.

    Requires: agents:create permission
    """

    async def event_generator():
        try:
            async for event_data in service.chat_for_agent_creation_stream(
                message=request.message,
                user_id=user.id,
                conversation_history=request.conversation_history,
                agent_id=request.agent_id,
            ):
                # Format as SSE event
                yield {"event": "message", "data": json.dumps(event_data)}
        except Exception as e:
            # Send error event
            yield {"event": "error", "data": json.dumps({"type": "error", "message": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/", response_model=list[AgentDetails])
async def list_agents(
    user: User = Depends(RequirePermission("agents:read")),
    service: AgentBuilderService = Depends(get_agent_builder_service),
):
    """
    List all agents owned by the current user.
    Superusers can see all agents.

    Requires: agents:read permission

    Note: Exceptions are handled by global exception handlers.
    """
    return await service.list_agents(user_id=user.id, is_superuser=user.is_superuser)


@router.get("/{agent_id}", response_model=AgentDetails)
async def get_agent(
    agent_id: str,
    user: User = Depends(RequirePermission("agents:read")),
    service: AgentBuilderService = Depends(get_agent_builder_service),
):
    """
    Get details of a specific agent.
    Users can only access their own agents unless they are superusers.

    Requires: agents:read permission

    Raises:
        AgentNotFoundError: If agent doesn't exist or user doesn't have access
    """
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)
    return agent


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    request: AgentExecuteRequest,
    user: User = Depends(RequirePermission("agents:execute")),
    service: AgentExecutionService = Depends(get_agent_execution_service),
):
    """
    Execute an agent.
    This is where users pay to run their created agents.

    Requires: agents:execute permission

    Note: Exceptions are handled by global exception handlers.
          ValueError from service is converted to AgentNotFoundError automatically.
    """
    result = await service.execute_agent(
        agent_id=request.agent_id, input_data=request.input_data
    )

    # Get the execution record for timestamps
    execution = await service.get_execution(result["execution_id"])

    return AgentExecuteResponse(
        execution_id=result["execution_id"],
        agent_id=request.agent_id,
        status=result["status"],
        result=result["result"],
        cost=result["cost"],
        started_at=execution.started_at if execution else datetime.utcnow(),
        completed_at=execution.completed_at if execution else datetime.utcnow(),
    )


# Build system endpoints

@router.post("/build/{agent_id}", response_model=schemas.BuildTriggerResponse)
async def trigger_build(
    agent_id: str,
    request: schemas.BuildTriggerRequest,
    user: User = Depends(RequirePermission("agents:build")),
    version_repo: repositories.AgentVersionRepository = Depends(dependencies.get_version_repository),
    build_pipeline: BuildPipeline = Depends(dependencies.get_build_pipeline),
    service: AgentBuilderService = Depends(dependencies.get_agent_builder_service),
):
    """
    Manually trigger a build for an agent's latest spec.

    Requires: agents:build permission

    Args:
        agent_id: Agent ID to build
        request: Build trigger options (force rebuild)
        user: Authenticated user
        version_repo: Version repository
        build_pipeline: Build pipeline
        service: Agent builder service

    Returns:
        Build trigger response with version ID and status

    Raises:
        AgentNotFoundError: If agent doesn't exist or user doesn't have access
    """
    # Check agent exists and user has access
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Check if version already exists
    latest_version = await version_repo.get_latest_version(agent_id)
    if latest_version and latest_version.build_status.value == "ready" and not request.force:
        return schemas.BuildTriggerResponse(
            version_id=latest_version.id,
            status=schemas.BuildStatus.READY,
            message="Agent already has a ready version. Use force=true to rebuild.",
        )

    # Parse spec from agent
    from src.blacklight.features.agents.spec_schema import AgentSpec

    if agent.graph_structure is None:
        raise HTTPException(status_code=400, detail="Agent has no graph structure to build")

    spec = AgentSpec(**agent.graph_structure)  # type: ignore[arg-type]

    # Trigger build
    version = await build_pipeline.run(agent_id, spec)

    return schemas.BuildTriggerResponse(
        version_id=version.id,
        status=schemas.BuildStatus(version.build_status.value),
        message=f"Build triggered for version {version.version}",
    )


@router.get("/{agent_id}/versions", response_model=list[schemas.AgentVersionResponse])
async def list_versions(
    agent_id: str,
    user: User = Depends(RequirePermission("agents:read")),
    version_repo: repositories.AgentVersionRepository = Depends(dependencies.get_version_repository),
    service: AgentBuilderService = Depends(dependencies.get_agent_builder_service),
):
    """
    List all versions for an agent.

    Requires: agents:read permission

    Args:
        agent_id: Agent ID
        user: Authenticated user
        version_repo: Version repository
        service: Agent builder service

    Returns:
        List of agent versions

    Raises:
        AgentNotFoundError: If agent doesn't exist or user doesn't have access
    """
    # Check agent access
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Get versions
    versions = await version_repo.get_versions_by_agent(agent_id)

    return [
        schemas.AgentVersionResponse(
            id=v.id,
            agent_id=v.agent_id,
            version=v.version,
            build_status=schemas.BuildStatus(v.build_status.value),
            code_path=v.code_path,
            metrics=v.metrics,
            error_details=v.error_details,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in versions
    ]


@router.get("/{agent_id}/versions/{version_id}", response_model=schemas.AgentVersionResponse)
async def get_version(
    agent_id: str,
    version_id: str,
    user: User = Depends(RequirePermission("agents:read")),
    version_repo: repositories.AgentVersionRepository = Depends(dependencies.get_version_repository),
    service: AgentBuilderService = Depends(dependencies.get_agent_builder_service),
):
    """
    Get a specific agent version.

    Requires: agents:read permission

    Args:
        agent_id: Agent ID
        version_id: Version ID
        user: Authenticated user
        version_repo: Version repository
        service: Agent builder service

    Returns:
        Agent version details

    Raises:
        AgentNotFoundError: If agent/version doesn't exist or user doesn't have access
    """
    # Check agent access
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Get version
    version = await version_repo.get_by_id(version_id)
    if not version or version.agent_id != agent_id:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    return schemas.AgentVersionResponse(
        id=version.id,
        agent_id=version.agent_id,
        version=version.version,
        build_status=schemas.BuildStatus(version.build_status.value),
        code_path=version.code_path,
        metrics=version.metrics,
        error_details=version.error_details,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.get("/{agent_id}/versions/{version_id}/logs", response_model=list[schemas.BuildLogResponse])
async def get_version_logs(
    agent_id: str,
    version_id: str,
    stage: str | None = None,
    user: User = Depends(RequirePermission("agents:read")),
    log_repo: repositories.AgentBuildLogRepository = Depends(dependencies.get_build_log_repository),
    service: AgentBuilderService = Depends(dependencies.get_agent_builder_service),
):
    """
    Get build logs for a version.

    Requires: agents:read permission

    Args:
        agent_id: Agent ID
        version_id: Version ID
        stage: Optional stage filter (compile, test, fixpass)
        user: Authenticated user
        log_repo: Build log repository
        service: Agent builder service

    Returns:
        List of build log entries

    Raises:
        AgentNotFoundError: If agent doesn't exist or user doesn't have access
    """
    # Check agent access
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Get logs
    logs = await log_repo.get_logs_by_version(version_id, stage=stage)

    return [
        schemas.BuildLogResponse(
            id=log.id,
            stage=log.stage,
            level=log.level,
            message=log.message,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.post("/{agent_id}/versions/{version_id}/test", response_model=schemas.TestRunResponse)
async def rerun_tests(
    agent_id: str,
    version_id: str,
    user: User = Depends(RequirePermission("agents:test")),
    version_repo: repositories.AgentVersionRepository = Depends(dependencies.get_version_repository),
    test_run_repo: repositories.AgentTestRunRepository = Depends(dependencies.get_test_run_repository),
    service: AgentBuilderService = Depends(dependencies.get_agent_builder_service),
):
    """
    Re-run tests for an agent version.

    Useful after tool configuration changes or to verify fixes.

    Requires: agents:test permission

    Args:
        agent_id: Agent ID
        version_id: Version ID
        user: Authenticated user
        version_repo: Version repository
        test_run_repo: Test run repository
        service: Agent builder service

    Returns:
        New test run result

    Raises:
        AgentNotFoundError: If agent/version doesn't exist or user doesn't have access
    """
    # Check agent access
    agent = await service.get_agent(agent_id, user_id=user.id, is_superuser=user.is_superuser)
    if agent is None:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Get version
    version = await version_repo.get_by_id(version_id)
    if not version or version.agent_id != agent_id:
        raise AgentNotFoundError(agent_id=agent_id, user_id=user.id)

    # Create test run
    from pathlib import Path
    from src.blacklight.features.agents.test_runner import AgentTestRunner
    from src.blacklight.features.agents.spec_schema import AgentSpec

    test_run = await test_run_repo.create_test_run(version_id)
    await test_run_repo.update_test_run(test_run.id, "RUNNING")

    # Run tests
    try:
        spec = AgentSpec(**version.spec)
        if version.code_path is None:
            raise HTTPException(status_code=400, detail="Agent version has no code path")
        code_path = Path(version.code_path)
        test_runner = AgentTestRunner()

        all_passed, report = await test_runner.run(code_path, spec)

        # Update test run
        await test_run_repo.update_test_run(
            test_run.id,
            status="PASSED" if all_passed else "FAILED",
            report=report,
            completed_at=datetime.utcnow(),
        )

        test_run = await test_run_repo.get_by_id(test_run.id)

    except Exception as e:
        await test_run_repo.update_test_run(
            test_run.id,
            status="FAILED",
            report={"error": str(e)},
            completed_at=datetime.utcnow(),
        )
        test_run = await test_run_repo.get_by_id(test_run.id)

    if test_run is None:
        raise HTTPException(status_code=404, detail="Test run not found after update")

    return schemas.TestRunResponse(
        id=test_run.id,
        status=test_run.status,
        report=test_run.report,
        created_at=test_run.created_at,
        completed_at=test_run.completed_at,
    )
