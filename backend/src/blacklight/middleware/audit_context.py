"""
Audit Context Middleware

Sets request-scoped context for audit logging using ContextVars.
This allows @audit_log decorators to access request information
without explicit parameter passing.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.blacklight.common.audit import set_db_context, set_request_context
from src.blacklight.common.database import SessionLocal


class AuditContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set audit context for each request

    Sets request, user, and database session in ContextVars for use
    by @audit_log decorators throughout the request lifecycle.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and set audit context

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response from the route handler
        """
        # Set request context
        set_request_context(request)

        # Create database session for the request
        async with SessionLocal() as session:
            # Set database context
            set_db_context(session)

            # Note: User context is set by the AuditLog dependency or route handler
            # We don't set it here because authentication happens in dependencies

            # Process the request
            response = await call_next(request)

            return response
