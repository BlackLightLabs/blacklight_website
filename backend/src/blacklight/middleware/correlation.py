"""
Request Correlation Middleware

Provides request correlation ID tracking and request/response logging.
Uses asgi-correlation-id for automatic UUID generation and propagation.
"""

import time
from typing import Callable

import structlog
from asgi_correlation_id import CorrelationIdMiddleware as BaseCorrelationIdMiddleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.blacklight.common.log_sampling import should_log_request

logger = structlog.get_logger("blacklight.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses with timing information.

    This middleware:
    - Logs incoming requests with method, path, and client IP
    - Tracks request duration
    - Logs response with status code and duration
    - Automatically includes correlation ID in all logs
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and log details with sampling for high-traffic endpoints."""
        # Extract request details
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Track request timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Check if request should be logged (sampling)
            if should_log_request(path, method, response.status_code):
                # Log incoming request
                logger.info(
                    "request_started",
                    method=method,
                    path=path,
                    client_ip=client_ip,
                    query_params=dict(request.query_params) if request.query_params else None,
                )

                # Log response
                logger.info(
                    "request_completed",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

            return response

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Always log errors (sampling bypassed)
            logger.error(
                "request_failed",
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                exc_info=True,
            )
            raise


# Re-export CorrelationIdMiddleware for convenience
CorrelationIdMiddleware = BaseCorrelationIdMiddleware
