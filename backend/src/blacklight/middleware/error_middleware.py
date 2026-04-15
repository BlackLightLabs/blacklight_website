"""
Error handling middleware for database rollback and request context

This middleware provides:
- Automatic database rollback on errors
- Additional safety net for unhandled exceptions
- Request context enrichment for error logging
"""

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.blacklight.common.database import SessionLocal

logger = structlog.get_logger("blacklight.middleware.error")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle database rollback and error recovery.

    This middleware:
    1. Ensures database sessions are rolled back on errors
    2. Provides a safety net for errors that bypass exception handlers
    3. Enriches error logs with request context

    Note: This runs BEFORE exception handlers, so it catches errors first.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and handle any errors.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from handler or error response
        """
        try:
            # Call next middleware/handler
            response = await call_next(request)
            return response

        except Exception as exc:
            # Log that we're catching an error before it goes to exception handlers
            logger.debug(
                "error_caught_by_middleware",
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
            )

            # Attempt to rollback any active database sessions
            # This is a safety measure - normally sessions are managed by FastAPI dependencies
            try:
                # Get any sessions that might be in request state
                if hasattr(request.state, "db"):
                    await request.state.db.rollback()
                    logger.info("database_rolled_back", path=request.url.path)
            except Exception as rollback_exc:
                logger.warning(
                    "database_rollback_failed",
                    error=str(rollback_exc),
                    path=request.url.path,
                )

            # Re-raise the exception so exception handlers can process it
            raise
