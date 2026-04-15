"""
OpenTelemetry Tracing Helpers

Provides convenience functions for creating and managing distributed traces.

Tracing Concepts:
- Trace: End-to-end request flow across services
- Span: Single operation within a trace (database query, API call, etc.)
- Attributes: Key-value metadata attached to spans
- Events: Point-in-time annotations within a span
- Context: Propagation of trace information across services

Usage:
    from src.blacklight.common.otel.tracing import (
        get_tracer,
        create_span,
        add_span_attribute,
        add_span_event,
        trace_function,
    )

    # Manual span creation
    tracer = get_tracer("blacklight.agents")
    with tracer.start_as_current_span("process_agent") as span:
        span.set_attribute("agent.id", agent_id)
        span.add_event("agent_validated")
        # ... do work ...

    # Or use decorator
    @trace_function("build_agent")
    async def build_agent(agent_id: str):
        ...
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable

import structlog
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.otel.tracing")


def get_tracer(name: str = "blacklight") -> Tracer:
    """
    Get OpenTelemetry Tracer for creating spans.

    Args:
        name: Name of the tracer (typically the library/module name)

    Returns:
        Tracer instance

    Example:
        tracer = get_tracer("blacklight.agents")
        with tracer.start_as_current_span("create_agent") as span:
            span.set_attribute("agent.type", "langgraph")
            # ... do work ...
    """
    return trace.get_tracer(
        instrumenting_module_name=name,
        instrumenting_library_version=settings.otel_service_version,
    )


def get_current_span() -> Span:
    """
    Get the currently active span.

    Returns:
        Current span, or a non-recording span if no span is active

    Example:
        span = get_current_span()
        span.set_attribute("custom.attribute", "value")
    """
    return trace.get_current_span()


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current span.

    Convenience function for adding metadata to the active span.

    Args:
        key: Attribute name
        value: Attribute value (string, int, float, bool, or list of these)

    Example:
        add_span_attribute("user.id", user_id)
        add_span_attribute("db.query_type", "select")
    """
    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """
    Add an event to the current span.

    Events are point-in-time annotations with optional attributes.
    Use them for important milestones within a span.

    Args:
        name: Event name
        attributes: Optional event attributes

    Example:
        add_span_event("cache_miss", {"cache.key": "user:123"})
        add_span_event("validation_failed", {"error": "invalid_email"})
    """
    span = get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_status(status_code: StatusCode, description: str = "") -> None:
    """
    Set the status of the current span.

    Args:
        status_code: StatusCode.OK, StatusCode.ERROR, or StatusCode.UNSET
        description: Optional status description (required for ERROR)

    Example:
        set_span_status(StatusCode.ERROR, "Database connection failed")
        set_span_status(StatusCode.OK)
    """
    span = get_current_span()
    if span and span.is_recording():
        span.set_status(Status(status_code=status_code, description=description))


def record_exception(exception: Exception, escaped: bool = False) -> None:
    """
    Record an exception in the current span.

    Args:
        exception: The exception to record
        escaped: Whether the exception escaped the span scope

    Example:
        try:
            # ... do work ...
        except ValueError as e:
            record_exception(e, escaped=True)
            raise
    """
    span = get_current_span()
    if span and span.is_recording():
        span.record_exception(exception, escaped=escaped)
        span.set_status(Status(status_code=StatusCode.ERROR, description=str(exception)))


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "blacklight",
):
    """
    Context manager for creating a span.

    Simpler alternative to tracer.start_as_current_span() for common cases.

    Args:
        name: Span name
        attributes: Optional span attributes
        tracer_name: Name of the tracer to use

    Yields:
        Span instance

    Example:
        with create_span("database_query", {"db.table": "users"}):
            # ... execute query ...
    """
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            record_exception(e, escaped=True)
            raise


def trace_function(
    span_name: str | None = None,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "blacklight",
    record_exception_flag: bool = True,
) -> Callable:
    """
    Decorator to automatically trace a function with a span.

    Creates a span for the entire function execution, automatically
    handling success and error cases.

    Args:
        span_name: Span name (defaults to function name)
        attributes: Static attributes to attach to span
        tracer_name: Name of the tracer to use
        record_exception_flag: Whether to record exceptions in span

    Returns:
        Decorator function

    Example:
        @trace_function("process_user_request", {"service": "api"})
        async def handle_request(user_id: int):
            add_span_attribute("user.id", user_id)
            # ... process request ...
    """
    def decorator(func: Callable) -> Callable:
        # Use function name as span name if not provided
        nonlocal span_name
        if span_name is None:
            span_name = func.__name__

        tracer = get_tracer(tracer_name)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                # Add static attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(status_code=StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception_flag:
                        record_exception(e, escaped=True)
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                # Add static attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(status_code=StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception_flag:
                        record_exception(e, escaped=True)
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_async_context(span_name: str, tracer_name: str = "blacklight"):
    """
    Async context manager for tracing code blocks.

    Similar to create_span but designed specifically for async code.

    Args:
        span_name: Name of the span
        tracer_name: Name of the tracer to use

    Example:
        async with trace_async_context("fetch_user_data"):
            user = await db.get_user(user_id)
            add_span_attribute("user.email", user.email)
    """
    tracer = get_tracer(tracer_name)
    return tracer.start_as_current_span(span_name)


# ============================================================================
# Common Span Attributes
# ============================================================================

class SpanAttributes:
    """
    Common span attribute keys following OpenTelemetry semantic conventions.

    Use these constants for consistent attribute naming across the application.
    """

    # General
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"

    # User
    USER_ID = "user.id"
    USER_EMAIL = "user.email"
    USER_ROLE = "user.role"

    # Agent
    AGENT_ID = "agent.id"
    AGENT_NAME = "agent.name"
    AGENT_STATUS = "agent.status"
    AGENT_VERSION = "agent.version"

    # Conversation
    CONVERSATION_ID = "conversation.id"
    MESSAGE_ROLE = "message.role"
    MESSAGE_LENGTH = "message.length"

    # Execution
    EXECUTION_ID = "execution.id"
    EXECUTION_STATUS = "execution.status"
    EXECUTION_DURATION = "execution.duration_seconds"

    # Database
    DB_SYSTEM = "db.system"
    DB_NAME = "db.name"
    DB_TABLE = "db.sql.table"
    DB_OPERATION = "db.operation"
    DB_STATEMENT = "db.statement"

    # HTTP
    HTTP_METHOD = "http.request.method"
    HTTP_STATUS_CODE = "http.response.status_code"
    HTTP_URL = "url.full"
    HTTP_TARGET = "url.path"

    # LLM
    LLM_PROVIDER = "llm.provider"
    LLM_MODEL = "llm.model"
    LLM_TOKENS = "llm.tokens"
    LLM_COST = "llm.cost_usd"


# ============================================================================
# Common Event Names
# ============================================================================

class SpanEvents:
    """
    Common span event names for consistency.

    Use these constants for important events that should be tracked in spans.
    """

    # Validation
    VALIDATION_STARTED = "validation.started"
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"

    # Cache
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    CACHE_WRITE = "cache.write"

    # Database
    DB_QUERY_STARTED = "db.query_started"
    DB_QUERY_COMPLETED = "db.query_completed"
    DB_TRANSACTION_STARTED = "db.transaction_started"
    DB_TRANSACTION_COMMITTED = "db.transaction_committed"
    DB_TRANSACTION_ROLLED_BACK = "db.transaction_rolled_back"

    # Authentication
    AUTH_STARTED = "auth.started"
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILED = "auth.failed"
    PERMISSION_CHECK = "permission.check"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"

    # Agent Operations
    AGENT_BUILD_STARTED = "agent.build_started"
    AGENT_BUILD_COMPLETED = "agent.build_completed"
    AGENT_EXECUTION_STARTED = "agent.execution_started"
    AGENT_EXECUTION_COMPLETED = "agent.execution_completed"

    # LLM Operations
    LLM_REQUEST_STARTED = "llm.request_started"
    LLM_REQUEST_COMPLETED = "llm.request_completed"
    LLM_STREAMING_STARTED = "llm.streaming_started"
    LLM_TOKEN_RECEIVED = "llm.token_received"
