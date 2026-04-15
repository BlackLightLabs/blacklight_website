"""
Request Processing Middleware

This package contains FastAPI middleware components for cross-cutting concerns
such as logging, error handling, CSRF protection, and audit context.

Available Middleware:
    - AuditContextMiddleware: Sets up context variables for audit logging
    - CorrelationIdMiddleware: Adds correlation IDs to requests for tracing
    - LoggingMiddleware: Structured logging for all requests
    - CSRFMiddleware: CSRF token validation for state-changing requests
    - ErrorHandlingMiddleware: Global error handling and formatting

Usage:
    Middleware is automatically registered in main.py:

    ```python
    from src.blacklight.middleware import (
        AuditContextMiddleware,
        CorrelationIdMiddleware,
        LoggingMiddleware,
        CSRFMiddleware,
        ErrorHandlingMiddleware,
        register_exception_handlers,
    )

    app.add_middleware(AuditContextMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    register_exception_handlers(app)
    ```

Middleware Execution Order:
    Middleware runs in reverse order of registration (LIFO):
    1. ErrorHandlingMiddleware (outer - catches all errors)
    2. CSRFMiddleware (validates CSRF tokens)
    3. LoggingMiddleware (logs requests/responses)
    4. CorrelationIdMiddleware (adds correlation IDs)
    5. AuditContextMiddleware (innermost - sets up audit context)

For more information on error handling, see backend/src/blacklight/common/exceptions.py.
"""

from .audit_context import AuditContextMiddleware
from .correlation import CorrelationIdMiddleware, LoggingMiddleware
from .csrf import CSRFMiddleware
from .error_handlers import register_exception_handlers
from .error_middleware import ErrorHandlingMiddleware

__all__ = [
    "AuditContextMiddleware",
    "CorrelationIdMiddleware",
    "LoggingMiddleware",
    "CSRFMiddleware",
    "ErrorHandlingMiddleware",
    "register_exception_handlers",
]
