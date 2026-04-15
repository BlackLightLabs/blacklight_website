"""
Database Query Performance Tracking

Logs slow queries and database metrics for production monitoring.
"""

import time
from typing import Any

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.database")

# Import OpenTelemetry metrics (with fallback if not available)
try:
    from src.blacklight.common.otel import (
        db_pool_checked_out_gauge,
        db_pool_size_gauge,
        db_query_duration_histogram,
        db_slow_queries_counter,
    )

    METRICS_ENABLED = True
except ImportError:
    # Metrics module not available yet
    METRICS_ENABLED = False


def setup_query_logging(engine: Engine) -> None:
    """
    Set up SQLAlchemy event listeners for query performance tracking.

    Logs:
    - Slow queries (configurable threshold)
    - Query execution times
    - Connection pool metrics

    Args:
        engine: SQLAlchemy engine to monitor
    """

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        context._query_start_time = time.time()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log query execution time and detect slow queries."""
        total_time = time.time() - context._query_start_time
        duration_ms = total_time * 1000
        duration_seconds = total_time
        is_slow = duration_ms > settings.slow_query_threshold_ms

        # Emit OpenTelemetry metrics
        if METRICS_ENABLED:
            db_query_duration_histogram.record(duration_seconds)
            if is_slow:
                db_slow_queries_counter.add(1)

        # Log all queries in debug mode
        if settings.log_level.upper() == "DEBUG":
            logger.debug(
                "database_query",
                query=statement[:200],  # Truncate long queries
                duration_ms=round(duration_ms, 2),
            )

        # Log slow queries (always, regardless of log level)
        if is_slow:
            logger.warning(
                "slow_query_detected",
                query=statement[:500],  # More context for slow queries
                duration_ms=round(duration_ms, 2),
                threshold_ms=settings.slow_query_threshold_ms,
                parameters=str(parameters)[:200] if parameters else None,
            )

    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new database connections."""
        logger.debug("database_connection_established")

    @event.listens_for(Pool, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track connection pool usage."""
        pool = connection_proxy._pool
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()

        # Emit OpenTelemetry metrics
        if METRICS_ENABLED:
            # Note: For gauges, we just set the current value
            # Since these are UpDownCounters, we need to track the delta
            # For now, we'll add the values (this may need adjustment based on actual usage)
            db_pool_size_gauge.add(pool_size)
            db_pool_checked_out_gauge.add(checked_out)

        logger.debug(
            "connection_pool_checkout",
            pool_size=pool_size,
            checked_out=checked_out,
            overflow=overflow,
        )


def log_query_stats(query_name: str, duration_ms: float, row_count: int | None = None) -> None:
    """
    Log custom query statistics.

    Use this for manual instrumentation of complex queries.

    Args:
        query_name: Descriptive name for the query
        duration_ms: Query duration in milliseconds
        row_count: Number of rows returned (optional)
    """
    log_data: dict[str, Any] = {
        "query_name": query_name,
        "duration_ms": round(duration_ms, 2),
    }

    if row_count is not None:
        log_data["row_count"] = row_count

    if duration_ms > settings.slow_query_threshold_ms:
        logger.warning("slow_custom_query", **log_data)
    else:
        logger.info("query_executed", **log_data)
