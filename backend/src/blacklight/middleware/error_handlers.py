"""
Global exception handlers for FastAPI

Provides centralized error handling for all exceptions raised in the application.
These handlers ensure consistent error responses and proper logging.

Register handlers in main.py using:
    from src.blacklight.middleware.error_handlers import register_exception_handlers
    register_exception_handlers(app)
"""

import traceback

import structlog
from asgi_correlation_id import correlation_id
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.blacklight.common.error_schemas import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from src.blacklight.common.exceptions import (
    BlacklightException,
    DatabaseError,
)
from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.error_handlers")


def get_request_id() -> str | None:
    """Get current request correlation ID."""
    return correlation_id.get()


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
) -> JSONResponse:
    """
    Create standardized error response.

    Args:
        code: Error code
        message: Error message
        status_code: HTTP status code
        details: Additional error details (excluded in production)

    Returns:
        JSONResponse with error details
    """
    error_detail = ErrorDetail(
        code=code,
        message=message,
        details=details if settings.expose_error_details else None,
        request_id=get_request_id(),
    )

    error_response = ErrorResponse(error=error_detail)

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def blacklight_exception_handler(
    request: Request, exc: BlacklightException
) -> JSONResponse:
    """
    Handle custom Blacklight exceptions.

    These are expected errors with well-defined error codes and messages.
    """
    # Log based on severity (4xx = warning, 5xx = error)
    if exc.status_code < 500:
        logger.warning(
            "client_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
            details=exc.details,
        )
    else:
        logger.error(
            "server_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
            details=exc.details,
        )

    return create_error_response(
        code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle standard HTTPException from FastAPI/Starlette.

    Maintains compatibility with existing FastAPI code.
    """
    # Convert detail to string if it's not already
    message = str(exc.detail) if exc.detail else "An error occurred"

    # Map status code to error code
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    # Log based on severity
    if exc.status_code < 500:
        logger.warning(
            "http_client_error",
            error_code=error_code,
            status_code=exc.status_code,
            path=request.url.path,
            message=message,
        )
    else:
        logger.error(
            "http_server_error",
            error_code=error_code,
            status_code=exc.status_code,
            path=request.url.path,
            message=message,
        )

    return create_error_response(
        code=error_code,
        message=message,
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Returns detailed validation errors to help clients fix their requests.
    """
    # Extract validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append(
            ValidationErrorDetail(
                loc=list(error["loc"]),
                msg=error["msg"],
                type=error["type"],
            )
        )

    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )

    error_detail = ErrorDetail(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=get_request_id(),
    )

    response = ValidationErrorResponse(
        error=error_detail,
        validation_errors=validation_errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump(exclude_none=True),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.

    Converts database exceptions to DatabaseError for consistent handling.
    """
    # Log the database error with full details
    logger.error(
        "database_error",
        path=request.url.path,
        error_type=type(exc).__name__,
        error=str(exc),
        exc_info=True,
    )

    # Convert to DatabaseError
    db_error = DatabaseError(
        message="A database error occurred. Please try again later.",
        original_error=exc,
    )

    return create_error_response(
        code=db_error.error_code,
        message=db_error.message,
        status_code=db_error.status_code,
        details=db_error.details if settings.expose_error_details else None,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    This is the catch-all handler for errors we didn't anticipate.
    Logs full stack trace for debugging.
    """
    # Get stack trace
    tb = traceback.format_exc()

    # Log the error with full context
    logger.error(
        "unexpected_error",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
        traceback=tb,
        exc_info=True,
    )

    # Don't expose internal error details to users in production
    if settings.expose_error_details:
        message = f"An unexpected error occurred: {str(exc)}"
        details = {
            "error_type": type(exc).__name__,
            "traceback": tb,
        }
    else:
        message = "An unexpected error occurred. Please contact support if the problem persists."
        details = None

    return create_error_response(
        code="INTERNAL_ERROR",
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with FastAPI app.

    Call this function in main.py after creating the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Custom Blacklight exceptions (highest priority)
    app.add_exception_handler(BlacklightException, blacklight_exception_handler)

    # FastAPI/Starlette exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # Catch-all for unexpected errors (lowest priority)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info(
        "exception_handlers_registered",
        handlers=[
            "BlacklightException",
            "StarletteHTTPException",
            "RequestValidationError",
            "SQLAlchemyError",
            "Exception (catch-all)",
        ],
    )
