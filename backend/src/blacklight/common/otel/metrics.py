"""
OpenTelemetry Metrics Helpers

Provides convenience functions for creating and recording metrics.

Metrics Types:
- Counter: Monotonically increasing value (e.g., total requests)
- UpDownCounter: Can increase or decrease (e.g., active connections)
- Histogram: Distribution of values (e.g., request duration)
- ObservableGauge: Async callback for current value (e.g., memory usage)

Usage:
    from src.blacklight.common.otel.metrics import (
        get_meter,
        create_counter,
        create_histogram,
        track_counter,
        track_histogram,
    )

    # Create metrics
    request_counter = create_counter(
        name="http_requests_total",
        description="Total HTTP requests",
        unit="requests",
    )

    # Record values
    request_counter.add(1, {"method": "GET", "status": "200"})

    # Or use decorators
    @track_counter("function_calls_total", description="Function call counter")
    async def my_function():
        ...
"""

import time
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable

import structlog
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.otel.metrics")

# Context variable for tracking operation start time
_operation_start_time: ContextVar[float] = ContextVar("operation_start_time", default=0.0)

# Metric cache to avoid recreating metrics
_metrics_cache: dict[str, Any] = {}


def get_meter(name: str = "blacklight") -> Meter:
    """
    Get OpenTelemetry Meter for creating metrics.

    Args:
        name: Name of the meter (typically the library/module name)

    Returns:
        Meter instance

    Example:
        meter = get_meter("blacklight.agents")
        counter = meter.create_counter("agent_created_total")
    """
    return metrics.get_meter(
        name=name,
        version=settings.otel_service_version,
    )


def create_counter(
    name: str,
    description: str = "",
    unit: str = "",
    meter_name: str = "blacklight",
) -> Counter:
    """
    Create a Counter metric.

    Counters are monotonically increasing values (never decrease).
    Use for counting events like requests, errors, tasks completed.

    Args:
        name: Metric name (e.g., "http_requests_total")
        description: Human-readable description
        unit: Unit of measurement (e.g., "requests", "bytes")
        meter_name: Name of the meter to use

    Returns:
        Counter instance

    Example:
        requests_counter = create_counter(
            name="http_requests_total",
            description="Total HTTP requests",
            unit="requests",
        )
        requests_counter.add(1, {"method": "GET", "status": "200"})
    """
    cache_key = f"counter:{meter_name}:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]

    meter = get_meter(meter_name)
    counter = meter.create_counter(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[cache_key] = counter
    return counter


def create_up_down_counter(
    name: str,
    description: str = "",
    unit: str = "",
    meter_name: str = "blacklight",
) -> UpDownCounter:
    """
    Create an UpDownCounter metric.

    UpDownCounters can increase or decrease.
    Use for tracking values that go up and down like active connections,
    queue size, items in cache.

    Args:
        name: Metric name (e.g., "active_connections")
        description: Human-readable description
        unit: Unit of measurement (e.g., "connections", "items")
        meter_name: Name of the meter to use

    Returns:
        UpDownCounter instance

    Example:
        active_conn = create_up_down_counter(
            name="active_connections",
            description="Currently active database connections",
            unit="connections",
        )
        active_conn.add(1)   # Connection opened
        active_conn.add(-1)  # Connection closed
    """
    cache_key = f"updowncounter:{meter_name}:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]

    meter = get_meter(meter_name)
    counter = meter.create_up_down_counter(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[cache_key] = counter
    return counter


def create_histogram(
    name: str,
    description: str = "",
    unit: str = "",
    meter_name: str = "blacklight",
) -> Histogram:
    """
    Create a Histogram metric.

    Histograms track distribution of values.
    Use for measuring durations, sizes, temperatures - anything with a range.

    Args:
        name: Metric name (e.g., "http_request_duration_seconds")
        description: Human-readable description
        unit: Unit of measurement (e.g., "seconds", "bytes", "ms")
        meter_name: Name of the meter to use

    Returns:
        Histogram instance

    Example:
        duration_histogram = create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration",
            unit="s",
        )
        duration_histogram.record(0.142, {"method": "GET", "status": "200"})
    """
    cache_key = f"histogram:{meter_name}:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]

    meter = get_meter(meter_name)
    histogram = meter.create_histogram(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[cache_key] = histogram
    return histogram


def track_counter(
    name: str,
    description: str = "",
    unit: str = "",
    meter_name: str = "blacklight",
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator to increment a counter every time a function is called.

    Args:
        name: Counter name
        description: Counter description
        unit: Unit of measurement
        meter_name: Meter name
        attributes: Static attributes to attach to all counter increments

    Returns:
        Decorator function

    Example:
        @track_counter(
            "user_login_total",
            description="Total user logins",
            attributes={"auth_method": "password"}
        )
        async def login_user(email: str, password: str):
            ...
    """
    counter = create_counter(name, description, unit, meter_name)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = await func(*args, **kwargs)
                counter.add(1, attributes or {})
                return result
            except Exception:
                # Still count the call even if it fails
                counter.add(1, attributes or {})
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = func(*args, **kwargs)
                counter.add(1, attributes or {})
                return result
            except Exception:
                # Still count the call even if it fails
                counter.add(1, attributes or {})
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_histogram(
    name: str,
    description: str = "",
    unit: str = "s",
    meter_name: str = "blacklight",
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator to track function execution duration with a histogram.

    Automatically measures how long a function takes to execute and
    records it in a histogram metric.

    Args:
        name: Histogram name
        description: Histogram description
        unit: Unit of measurement (default: "s" for seconds)
        meter_name: Meter name
        attributes: Static attributes to attach to all measurements

    Returns:
        Decorator function

    Example:
        @track_histogram(
            "db_query_duration_seconds",
            description="Database query duration",
            attributes={"operation": "select"}
        )
        async def query_users():
            ...
    """
    histogram = create_histogram(name, description, unit, meter_name)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                histogram.record(duration, attributes or {})
                return result
            except Exception:
                duration = time.time() - start_time
                histogram.record(duration, attributes or {})
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                histogram.record(duration, attributes or {})
                return result
            except Exception:
                duration = time.time() - start_time
                histogram.record(duration, attributes or {})
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_errors(
    name: str = "errors_total",
    description: str = "Total errors",
    meter_name: str = "blacklight",
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator to track function errors with a counter.

    Increments counter only when the function raises an exception.

    Args:
        name: Counter name
        description: Counter description
        meter_name: Meter name
        attributes: Static attributes to attach to all counter increments

    Returns:
        Decorator function

    Example:
        @track_errors(
            "api_errors_total",
            description="Total API errors",
            attributes={"api": "llm"}
        )
        async def call_llm_api():
            ...
    """
    counter = create_counter(name, description, "errors", meter_name)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_attrs = (attributes or {}).copy()
                error_attrs["error_type"] = type(e).__name__
                counter.add(1, error_attrs)
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_attrs = (attributes or {}).copy()
                error_attrs["error_type"] = type(e).__name__
                counter.add(1, error_attrs)
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Business Metrics Helpers
# ============================================================================

# User metrics
users_registered_counter = create_counter(
    name="users_registered_total",
    description="Total users registered",
    unit="users",
)

user_logins_counter = create_counter(
    name="user_logins_total",
    description="Total user login attempts",
    unit="logins",
)

user_logouts_counter = create_counter(
    name="user_logouts_total",
    description="Total user logouts",
    unit="logouts",
)

password_resets_counter = create_counter(
    name="password_resets_total",
    description="Total password reset attempts",
    unit="resets",
)

permissions_denied_counter = create_counter(
    name="permissions_denied_total",
    description="Total permission denials",
    unit="denials",
)

# Agent metrics
agents_created_counter = create_counter(
    name="agents_created_total",
    description="Total agents created",
    unit="agents",
)

agents_updated_counter = create_counter(
    name="agents_updated_total",
    description="Total agents updated",
    unit="updates",
)

agents_deleted_counter = create_counter(
    name="agents_deleted_total",
    description="Total agents deleted",
    unit="agents",
)

agent_builds_counter = create_counter(
    name="agent_builds_total",
    description="Total agent builds",
    unit="builds",
)

agent_build_duration_histogram = create_histogram(
    name="agent_build_duration_seconds",
    description="Agent build duration",
    unit="s",
)

# Execution metrics
agent_executions_counter = create_counter(
    name="agent_executions_total",
    description="Total agent executions",
    unit="executions",
)

agent_execution_duration_histogram = create_histogram(
    name="agent_execution_duration_seconds",
    description="Agent execution duration",
    unit="s",
)

# Conversation metrics
conversations_started_counter = create_counter(
    name="conversations_started_total",
    description="Total conversations started",
    unit="conversations",
)

messages_sent_counter = create_counter(
    name="messages_sent_total",
    description="Total messages sent",
    unit="messages",
)

# Database metrics
db_query_duration_histogram = create_histogram(
    name="db_query_duration_seconds",
    description="Database query duration",
    unit="s",
)

db_slow_queries_counter = create_counter(
    name="db_slow_queries_total",
    description="Total slow database queries",
    unit="queries",
)

db_pool_size_gauge = create_up_down_counter(
    name="db_pool_size",
    description="Database connection pool size",
    unit="connections",
)

db_pool_checked_out_gauge = create_up_down_counter(
    name="db_pool_checked_out",
    description="Database connections currently checked out",
    unit="connections",
)

db_errors_counter = create_counter(
    name="db_errors_total",
    description="Total database errors",
    unit="errors",
)

# Circuit breaker metrics
circuit_breaker_state_gauge = create_up_down_counter(
    name="circuit_breaker_state",
    description="Circuit breaker state (0=closed, 1=half_open, 2=open)",
    unit="state",
)

circuit_breaker_failures_counter = create_counter(
    name="circuit_breaker_failures_total",
    description="Total circuit breaker failures",
    unit="failures",
)

circuit_breaker_successes_counter = create_counter(
    name="circuit_breaker_successes_total",
    description="Total circuit breaker successes",
    unit="successes",
)

circuit_breaker_opened_counter = create_counter(
    name="circuit_breaker_opened_total",
    description="Total times circuit breaker opened",
    unit="events",
)

circuit_breaker_closed_counter = create_counter(
    name="circuit_breaker_closed_total",
    description="Total times circuit breaker closed",
    unit="events",
)
