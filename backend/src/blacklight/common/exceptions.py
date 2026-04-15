"""
Custom exception hierarchy for Blacklight

This module provides domain-specific exceptions that enable graceful error
handling and recovery. Each exception includes:
- HTTP status code for API responses
- Error code for client-side error handling
- User-friendly message
- Optional details for debugging

Usage:
    raise NotFoundError(
        message="Agent not found",
        error_code="AGENT_NOT_FOUND",
        details={"agent_id": agent_id}
    )
"""

from typing import Any


class BlacklightException(Exception):
    """
    Base exception for all Blacklight application errors.

    This exception should be subclassed for specific error types.
    It provides a consistent interface for error handling and logging.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize exception with error details.

        Args:
            message: User-friendly error message
            error_code: Machine-readable error code for client handling
            status_code: HTTP status code for API response
            details: Additional context for debugging (not shown to users in production)
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation of error."""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"status_code={self.status_code}, "
            f"details={self.details!r})"
        )


# ============================================================================
# Client Errors (4xx) - User can fix these
# ============================================================================


class NotFoundError(BlacklightException):
    """
    Resource not found (404).

    Use when a requested resource doesn't exist or user doesn't have access.
    """

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=404, details=details
        )


class ValidationError(BlacklightException):
    """
    Input validation failed (422).

    Use when user input is invalid or doesn't meet business rules.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=422, details=details
        )


class PermissionDeniedError(BlacklightException):
    """
    User lacks required permission (403).

    Use when user is authenticated but not authorized for the action.
    """

    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "PERMISSION_DENIED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=403, details=details
        )


class AuthenticationError(BlacklightException):
    """
    Authentication failed (401).

    Use when user is not authenticated or token is invalid/expired.
    """

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "AUTHENTICATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=401, details=details
        )


class ConflictError(BlacklightException):
    """
    Resource conflict (409).

    Use when operation conflicts with current state (e.g., duplicate resource).
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=409, details=details
        )


class RateLimitError(BlacklightException):
    """
    Rate limit exceeded (429).

    Use when user has made too many requests in a given timeframe.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=429, details=details
        )


# ============================================================================
# Server Errors (5xx) - System errors, may be transient
# ============================================================================


class DatabaseError(BlacklightException):
    """
    Database operation failed (503).

    Use for database connection issues, timeouts, or query errors.
    These are often transient and may succeed on retry.
    """

    def __init__(
        self,
        message: str = "Database error occurred",
        error_code: str = "DATABASE_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        if details is None:
            details = {}
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message, error_code=error_code, status_code=503, details=details
        )
        self.original_error = original_error


class ExternalServiceError(BlacklightException):
    """
    External service call failed (503).

    Use for LLM API failures, third-party API errors, etc.
    These are often transient and may succeed on retry.
    """

    def __init__(
        self,
        message: str = "External service unavailable",
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
        service_name: str | None = None,
        original_error: Exception | None = None,
    ):
        if details is None:
            details = {}
        if service_name:
            details["service"] = service_name
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message, error_code=error_code, status_code=503, details=details
        )
        self.service_name = service_name
        self.original_error = original_error


class CircuitBreakerOpenError(BlacklightException):
    """
    Circuit breaker is open (503).

    Use when circuit breaker prevents call to failing service.
    Indicates the service is temporarily unavailable due to repeated failures.
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: str = "CIRCUIT_BREAKER_OPEN",
        details: dict[str, Any] | None = None,
        service_name: str | None = None,
    ):
        if details is None:
            details = {}
        if service_name:
            details["service"] = service_name

        super().__init__(
            message=message, error_code=error_code, status_code=503, details=details
        )
        self.service_name = service_name


# ============================================================================
# Fatal Configuration Errors - These should crash the app
# ============================================================================


class ConfigurationError(BlacklightException):
    """
    Fatal configuration error (500).

    Use for missing required environment variables or invalid configuration.
    These errors should cause the application to fail during startup.

    DO NOT catch this exception - let it crash the app so it can be fixed.
    """

    def __init__(
        self,
        message: str = "Configuration error",
        error_code: str = "CONFIGURATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message, error_code=error_code, status_code=500, details=details
        )


# ============================================================================
# Specialized Exceptions
# ============================================================================


class AgentNotFoundError(NotFoundError):
    """Agent-specific not found error."""

    def __init__(self, agent_id: str, user_id: int | None = None):
        details: dict[str, Any] = {"agent_id": agent_id}
        if user_id is not None:
            details["user_id"] = user_id

        super().__init__(
            message=f"Agent {agent_id} not found",
            error_code="AGENT_NOT_FOUND",
            details=details,
        )


class ConversationNotFoundError(NotFoundError):
    """Conversation-specific not found error."""

    def __init__(self, conversation_id: str):
        super().__init__(
            message=f"Conversation {conversation_id} not found",
            error_code="CONVERSATION_NOT_FOUND",
            details={"conversation_id": conversation_id},
        )


class UserNotFoundError(NotFoundError):
    """User-specific not found error."""

    def __init__(self, user_id: int | None = None, email: str | None = None):
        details: dict[str, Any] = {}
        if user_id is not None:
            details["user_id"] = user_id
        if email is not None:
            details["email"] = email

        super().__init__(
            message="User not found", error_code="USER_NOT_FOUND", details=details
        )


class RoleNotFoundError(NotFoundError):
    """Role-specific not found error."""

    def __init__(self, role_id: int | None = None, role_name: str | None = None):
        details: dict[str, Any] = {}
        if role_id is not None:
            details["role_id"] = role_id
        if role_name is not None:
            details["role_name"] = role_name

        super().__init__(
            message="Role not found", error_code="ROLE_NOT_FOUND", details=details
        )


class LLMError(ExternalServiceError):
    """LLM API-specific error."""

    def __init__(
        self,
        message: str = "LLM API call failed",
        provider: str | None = None,
        original_error: Exception | None = None,
    ):
        details = {}
        if provider:
            details["provider"] = provider

        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            details=details,
            service_name=f"LLM ({provider})" if provider else "LLM",
            original_error=original_error,
        )
