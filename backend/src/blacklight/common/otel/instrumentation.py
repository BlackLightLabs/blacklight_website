"""
OpenTelemetry Auto-Instrumentation

Sets up automatic instrumentation for FastAPI, SQLAlchemy, HTTPX, and other libraries.

Auto-instrumentation automatically creates spans for:
- HTTP requests (incoming and outgoing)
- Database queries
- Background tasks

Usage:
    from src.blacklight.common.otel.instrumentation import setup_instrumentation

    app = FastAPI()
    setup_instrumentation(app)
"""

import structlog
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.otel.instrumentation")

# Track whether instrumentation has been set up
_instrumentation_initialized = False


def setup_fastapi_instrumentation(app: FastAPI) -> None:
    """
    Set up FastAPI auto-instrumentation.

    Automatically creates spans for all HTTP requests with:
    - HTTP method, path, status code
    - Request/response headers (configurable)
    - Request/response body (configurable)
    - Client IP address

    Args:
        app: FastAPI application instance

    Example:
        app = FastAPI()
        setup_fastapi_instrumentation(app)
    """
    logger.info("setting_up_fastapi_instrumentation")

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/",  # Don't trace health checks
        tracer_provider=None,  # Use global tracer provider
    )

    logger.info("fastapi_instrumentation_complete")


def setup_sqlalchemy_instrumentation(engine=None) -> None:
    """
    Set up SQLAlchemy auto-instrumentation.

    Automatically creates spans for all database queries with:
    - SQL statement (can be sanitized)
    - Database name
    - Query duration
    - Row count

    Args:
        engine: Optional SQLAlchemy engine to instrument
                If not provided, instruments all engines

    Example:
        from src.blacklight.common.database import engine
        setup_sqlalchemy_instrumentation(engine)
    """
    logger.info("setting_up_sqlalchemy_instrumentation")

    if engine:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,  # Use sync engine for instrumentation
            tracer_provider=None,  # Use global tracer provider
            enable_commenter=True,  # Add trace context to SQL comments
        )
    else:
        SQLAlchemyInstrumentor().instrument(
            tracer_provider=None,
            enable_commenter=True,
        )

    logger.info("sqlalchemy_instrumentation_complete")


def setup_httpx_instrumentation() -> None:
    """
    Set up HTTPX auto-instrumentation.

    Automatically creates spans for all outgoing HTTP requests made with httpx.

    This is useful for tracing calls to external APIs like LLM providers.

    Example:
        setup_httpx_instrumentation()

        # Now all httpx requests are automatically traced
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com")
    """
    logger.info("setting_up_httpx_instrumentation")

    HTTPXClientInstrumentor().instrument(
        tracer_provider=None,  # Use global tracer provider
    )

    logger.info("httpx_instrumentation_complete")


def setup_instrumentation(app: FastAPI, engine=None) -> None:
    """
    Set up all auto-instrumentation.

    Call this once at application startup to instrument:
    - FastAPI (HTTP requests)
    - SQLAlchemy (database queries)
    - HTTPX (outgoing HTTP requests)

    Args:
        app: FastAPI application instance
        engine: Optional SQLAlchemy engine to instrument

    Example:
        from src.blacklight.common.otel.instrumentation import setup_instrumentation
        from src.blacklight.common.database import engine

        app = FastAPI()
        setup_instrumentation(app, engine)
    """
    global _instrumentation_initialized

    if _instrumentation_initialized:
        logger.warning("instrumentation_already_initialized")
        return

    if not settings.otel_enabled:
        logger.info("opentelemetry_disabled_skipping_instrumentation")
        return

    logger.info("setting_up_auto_instrumentation")

    try:
        # Set up FastAPI instrumentation
        setup_fastapi_instrumentation(app)

        # Set up SQLAlchemy instrumentation
        setup_sqlalchemy_instrumentation(engine)

        # Set up HTTPX instrumentation (for LLM API calls)
        setup_httpx_instrumentation()

        _instrumentation_initialized = True
        logger.info("auto_instrumentation_complete")

    except Exception as e:
        logger.error(
            "auto_instrumentation_failed",
            error=str(e),
            exc_info=True,
        )
        raise


def is_instrumentation_initialized() -> bool:
    """Check if instrumentation has been initialized."""
    return _instrumentation_initialized
