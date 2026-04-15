"""
OpenTelemetry Observability Module

Unified observability with OpenTelemetry for metrics and distributed tracing.

This module provides:
- Automatic instrumentation for FastAPI, SQLAlchemy, and HTTPX
- Custom metrics (counters, histograms, gauges)
- Distributed tracing with spans
- Multiple exporter support (Console, OTLP, Prometheus)

Quick Start:
    # In main.py
    from src.blacklight.common.otel import setup_otel

    app = FastAPI()
    setup_otel(app, engine)

    # Metrics will now be collected automatically
    # Traces will be created for all HTTP requests and DB queries

Custom Metrics:
    from src.blacklight.common.otel import (
        create_counter,
        create_histogram,
        track_counter,
        track_histogram,
    )

    # Create a counter
    my_counter = create_counter("my_events_total", "My event counter")
    my_counter.add(1, {"type": "important"})

    # Use decorator
    @track_counter("function_calls_total")
    async def my_function():
        ...

Distributed Tracing:
    from src.blacklight.common.otel import (
        create_span,
        add_span_attribute,
        trace_function,
    )

    # Manual span
    with create_span("my_operation") as span:
        add_span_attribute("user.id", user_id)
        # ... do work ...

    # Or use decorator
    @trace_function("process_data")
    async def process_data():
        ...

Available Metrics:
    Business Metrics:
    - users_registered_total
    - user_logins_total
    - agents_created_total
    - agent_executions_total
    - conversations_started_total

    Database Metrics:
    - db_query_duration_seconds
    - db_slow_queries_total
    - db_pool_size
    - db_errors_total

    Circuit Breaker Metrics:
    - circuit_breaker_state
    - circuit_breaker_failures_total
    - circuit_breaker_opened_total

Configuration:
    # In .env
    OTEL_ENABLED=true
    OTEL_SERVICE_NAME=blacklight
    OTEL_METRICS_EXPORTER=console  # or otlp, prometheus
    OTEL_TRACES_EXPORTER=console   # or otlp, jaeger
    OTEL_OTLP_ENDPOINT=http://localhost:4317
"""

import structlog
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.responses import Response

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.otel")

# Re-export commonly used functions
from .config import (  # noqa: E402
    get_meter_provider,
    get_resource,
    get_tracer_provider,
    setup_telemetry,
    shutdown_telemetry,
)
from .instrumentation import setup_instrumentation  # noqa: E402
from .metrics import (  # noqa: E402
    # Pre-created business metrics
    agent_build_duration_histogram,
    agent_builds_counter,
    agent_execution_duration_histogram,
    agent_executions_counter,
    agents_created_counter,
    agents_deleted_counter,
    agents_updated_counter,
    circuit_breaker_closed_counter,
    circuit_breaker_failures_counter,
    circuit_breaker_opened_counter,
    circuit_breaker_state_gauge,
    circuit_breaker_successes_counter,
    conversations_started_counter,
    # Metric creation functions
    create_counter,
    create_histogram,
    create_up_down_counter,
    db_errors_counter,
    # Pre-created database metrics
    db_pool_checked_out_gauge,
    db_pool_size_gauge,
    db_query_duration_histogram,
    db_slow_queries_counter,
    # Decorator functions
    get_meter,
    messages_sent_counter,
    password_resets_counter,
    permissions_denied_counter,
    track_counter,
    track_errors,
    track_histogram,
    user_logins_counter,
    user_logouts_counter,
    # Pre-created user metrics
    users_registered_counter,
)
from .tracing import (  # noqa: E402
    # Tracing creation functions
    add_span_attribute,
    add_span_event,
    create_span,
    get_current_span,
    get_tracer,
    record_exception,
    set_span_status,
    # Constants
    SpanAttributes,
    SpanEvents,
    # Decorator functions
    trace_async_context,
    trace_function,
)

__all__ = [
    # Setup functions
    "setup_otel",
    "shutdown_otel",
    # Config functions
    "setup_telemetry",
    "shutdown_telemetry",
    "get_meter_provider",
    "get_tracer_provider",
    "get_resource",
    # Instrumentation
    "setup_instrumentation",
    # Metrics - Creation
    "get_meter",
    "create_counter",
    "create_histogram",
    "create_up_down_counter",
    # Metrics - Decorators
    "track_counter",
    "track_histogram",
    "track_errors",
    # Metrics - Pre-created business metrics
    "users_registered_counter",
    "user_logins_counter",
    "user_logouts_counter",
    "password_resets_counter",
    "permissions_denied_counter",
    "agents_created_counter",
    "agents_updated_counter",
    "agents_deleted_counter",
    "agent_builds_counter",
    "agent_build_duration_histogram",
    "agent_executions_counter",
    "agent_execution_duration_histogram",
    "conversations_started_counter",
    "messages_sent_counter",
    # Metrics - Pre-created database metrics
    "db_query_duration_histogram",
    "db_slow_queries_counter",
    "db_pool_size_gauge",
    "db_pool_checked_out_gauge",
    "db_errors_counter",
    # Metrics - Pre-created circuit breaker metrics
    "circuit_breaker_state_gauge",
    "circuit_breaker_failures_counter",
    "circuit_breaker_successes_counter",
    "circuit_breaker_opened_counter",
    "circuit_breaker_closed_counter",
    # Tracing - Creation
    "get_tracer",
    "get_current_span",
    "create_span",
    "add_span_attribute",
    "add_span_event",
    "set_span_status",
    "record_exception",
    # Tracing - Decorators
    "trace_function",
    "trace_async_context",
    # Tracing - Constants
    "SpanAttributes",
    "SpanEvents",
]


def setup_otel(app: FastAPI, engine=None) -> None:
    """
    Set up OpenTelemetry for the application.

    This function:
    1. Initializes OpenTelemetry SDK (metrics and tracing)
    2. Sets up auto-instrumentation (FastAPI, SQLAlchemy, HTTPX)
    3. Adds /metrics endpoint (if Prometheus exporter enabled)

    Call this once at application startup.

    Args:
        app: FastAPI application instance
        engine: Optional SQLAlchemy engine for instrumentation

    Example:
        from src.blacklight.common.otel import setup_otel
        from src.blacklight.common.database import engine

        app = FastAPI()
        setup_otel(app, engine)
    """
    if not settings.otel_enabled:
        logger.info("opentelemetry_disabled")
        return

    logger.info(
        "setting_up_opentelemetry",
        service_name=settings.otel_service_name,
        metrics_exporter=settings.otel_metrics_exporter,
        traces_exporter=settings.otel_traces_exporter,
    )

    try:
        # Initialize OpenTelemetry SDK
        setup_telemetry()

        # Set up auto-instrumentation
        setup_instrumentation(app, engine)

        # Add /metrics endpoint if Prometheus exporter is enabled
        if settings.otel_metrics_exporter.lower() == "prometheus":
            @app.get("/metrics", include_in_schema=False)
            async def metrics() -> Response:
                """
                Prometheus metrics endpoint.

                Returns metrics in Prometheus text format.
                """
                metrics_output = generate_latest(REGISTRY)

                return Response(
                    content=metrics_output,
                    media_type=CONTENT_TYPE_LATEST,
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )

            logger.info("prometheus_metrics_endpoint_added", path="/metrics")

        logger.info("opentelemetry_setup_complete")

    except Exception as e:
        logger.error(
            "opentelemetry_setup_failed",
            error=str(e),
            exc_info=True,
        )
        raise


def shutdown_otel() -> None:
    """
    Shut down OpenTelemetry and flush pending data.

    Call this on application shutdown to ensure all telemetry data is exported.

    Example:
        # In main.py lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            setup_otel(app, engine)
            yield
            shutdown_otel()
    """
    if not settings.otel_enabled:
        return

    logger.info("shutting_down_opentelemetry")
    shutdown_telemetry()
