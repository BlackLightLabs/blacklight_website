"""
Business Event Logging

Centralized logging for business-critical events for analytics and monitoring.

These events help answer questions like:
- How many users registered today?
- Which agents are being created most?
- What's the agent execution success rate?
- Are users hitting permission errors?

All business events emit both logs AND Prometheus metrics for observability.
"""

from typing import Any

import structlog

# Get loggers for different business domains
auth_events = structlog.get_logger("blacklight.events.auth")
agent_events = structlog.get_logger("blacklight.events.agents")
execution_events = structlog.get_logger("blacklight.events.executions")

# Import OpenTelemetry business metrics
try:
    from src.blacklight.common.otel import (
        agent_build_duration_histogram,
        agent_builds_counter,
        agent_execution_duration_histogram,
        agent_executions_counter,
        agents_created_counter,
        agents_deleted_counter,
        agents_updated_counter,
        conversations_started_counter,
        messages_sent_counter,
        password_resets_counter,
        permissions_denied_counter,
        user_logins_counter,
        user_logouts_counter,
        users_registered_counter,
    )

    METRICS_ENABLED = True
except ImportError:
    # Metrics module not available yet
    METRICS_ENABLED = False


# ============================================================================
# Authentication & User Events
# ============================================================================

def log_user_registered(user_id: int, email: str, registration_method: str = "email") -> None:
    """
    Log user registration event.

    Args:
        user_id: ID of the newly registered user
        email: User's email (will be sanitized by logging pipeline)
        registration_method: "email", "github", "google", etc.
    """
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        users_registered_counter.add(1, {"registration_method": registration_method})

    auth_events.info(
        "user_registered",
        user_id=user_id,
        email=email,
        registration_method=registration_method,
    )


def log_user_login(user_id: int, login_method: str = "password", success: bool = True) -> None:
    """
    Log user login attempt.

    Args:
        user_id: User ID
        login_method: "password", "github", "google", etc.
        success: Whether login was successful
    """
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        status = "success" if success else "failed"
        user_logins_counter.add(1, {"login_method": login_method, "status": status})

    event = "user_login_success" if success else "user_login_failed"
    auth_events.info(event, user_id=user_id, login_method=login_method)


def log_user_logout(user_id: int) -> None:
    """Log user logout event."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        user_logouts_counter.add(1)

    auth_events.info("user_logout", user_id=user_id)


def log_password_reset(user_id: int, success: bool = True) -> None:
    """Log password reset event."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        status = "success" if success else "failed"
        password_resets_counter.add(1, {"status": status})

    event = "password_reset_success" if success else "password_reset_failed"
    auth_events.info(event, user_id=user_id)


def log_permission_denied(user_id: int, resource: str, action: str, path: str | None = None) -> None:
    """
    Log permission denial for security monitoring.

    Args:
        user_id: User who was denied
        resource: Resource they tried to access (e.g., "agents")
        action: Action they tried to perform (e.g., "delete")
        path: API path where denial occurred
    """
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        permissions_denied_counter.add(1, {"resource": resource, "action": action})

    auth_events.warning(
        "permission_denied",
        user_id=user_id,
        resource=resource,
        action=action,
        path=path,
    )


# ============================================================================
# Agent Events
# ============================================================================

def log_agent_created(
    agent_id: str,
    user_id: int,
    description: str | None = None,
    spec_summary: dict[str, Any] | None = None,
) -> None:
    """
    Log agent creation event.

    Args:
        agent_id: ID of the created agent
        user_id: User who created it
        description: Agent description
        spec_summary: Summary of agent spec (tools, models, etc.)
    """
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        agents_created_counter.add(1)

    agent_events.info(
        "agent_created",
        agent_id=agent_id,
        user_id=user_id,
        description=description,
        spec_summary=spec_summary,
    )


def log_agent_updated(agent_id: str, user_id: int, changes: dict[str, Any] | None = None) -> None:
    """Log agent update event."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        agents_updated_counter.add(1)

    agent_events.info(
        "agent_updated",
        agent_id=agent_id,
        user_id=user_id,
        changes=changes,
    )


def log_agent_deleted(agent_id: str, user_id: int) -> None:
    """Log agent deletion event."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        agents_deleted_counter.add(1)

    agent_events.info(
        "agent_deleted",
        agent_id=agent_id,
        user_id=user_id,
    )


def log_agent_build_started(agent_id: str, version: int) -> None:
    """Log agent build started."""
    agent_events.info(
        "agent_build_started",
        agent_id=agent_id,
        version=version,
    )


def log_agent_build_completed(
    agent_id: str,
    version: int,
    success: bool,
    duration_seconds: float | None = None,
    error: str | None = None,
) -> None:
    """Log agent build completion."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        status = "success" if success else "failed"
        agent_builds_counter.add(1, {"status": status})
        if duration_seconds is not None:
            agent_build_duration_histogram.record(duration_seconds)

    event = "agent_build_success" if success else "agent_build_failed"
    agent_events.info(
        event,
        agent_id=agent_id,
        version=version,
        duration_seconds=duration_seconds,
        error=error,
    )


# ============================================================================
# Execution Events
# ============================================================================

def log_agent_execution_started(
    execution_id: str,
    agent_id: str,
    user_id: int,
) -> None:
    """Log agent execution started."""
    execution_events.info(
        "agent_execution_started",
        execution_id=execution_id,
        agent_id=agent_id,
        user_id=user_id,
    )


def log_agent_execution_completed(
    execution_id: str,
    agent_id: str,
    user_id: int,
    success: bool,
    duration_seconds: float,
    cost: float | None = None,
    error: str | None = None,
) -> None:
    """
    Log agent execution completion.

    Args:
        execution_id: Execution ID
        agent_id: Agent ID
        user_id: User ID
        success: Whether execution succeeded
        duration_seconds: How long it took
        cost: Cost in USD
        error: Error message if failed
    """
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        status = "success" if success else "failed"
        agent_executions_counter.add(1, {"status": status})
        agent_execution_duration_histogram.record(duration_seconds)

    event = "agent_execution_success" if success else "agent_execution_failed"
    execution_events.info(
        event,
        execution_id=execution_id,
        agent_id=agent_id,
        user_id=user_id,
        duration_seconds=round(duration_seconds, 2),
        cost=cost,
        error=error,
    )


# ============================================================================
# Conversation Events
# ============================================================================

def log_conversation_started(
    conversation_id: str,
    agent_id: str,
    user_id: int,
) -> None:
    """Log conversation started."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        conversations_started_counter.add(1)

    agent_events.info(
        "conversation_started",
        conversation_id=conversation_id,
        agent_id=agent_id,
        user_id=user_id,
    )


def log_message_sent(
    conversation_id: str,
    role: str,
    message_length: int,
) -> None:
    """Log message sent in conversation."""
    # Emit OpenTelemetry metric
    if METRICS_ENABLED:
        messages_sent_counter.add(1, {"role": role})

    agent_events.debug(
        "message_sent",
        conversation_id=conversation_id,
        role=role,
        message_length=message_length,
    )


# ============================================================================
# System Health Events
# ============================================================================

def log_health_check(
    endpoint: str,
    status: str = "healthy",
    response_time_ms: float | None = None,
) -> None:
    """
    Log health check result.

    Args:
        endpoint: Health check endpoint
        status: "healthy", "degraded", "unhealthy"
        response_time_ms: Response time in milliseconds
    """
    logger = structlog.get_logger("blacklight.events.health")
    logger.info(
        "health_check",
        endpoint=endpoint,
        status=status,
        response_time_ms=response_time_ms,
    )
