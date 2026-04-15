"""
Error response schemas for consistent API error handling

Provides Pydantic models for standardized error responses across all endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Detailed error information.

    This model provides a consistent structure for error responses
    that can be easily parsed by clients.
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'AGENT_NOT_FOUND')",
        examples=["AGENT_NOT_FOUND", "VALIDATION_ERROR", "DATABASE_ERROR"],
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Agent not found", "Validation failed", "Database connection lost"],
    )

    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional context for debugging (excluded in production)",
        examples=[{"agent_id": "abc123", "user_id": 42}],
    )

    request_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "AGENT_NOT_FOUND",
                "message": "Agent abc123 not found",
                "details": {"agent_id": "abc123", "user_id": 42},
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response wrapper.

    All API errors return this structure for consistency.
    """

    error: ErrorDetail = Field(
        ..., description="Error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "AGENT_NOT_FOUND",
                    "message": "Agent abc123 not found",
                    "details": {"agent_id": "abc123"},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            }
        }


class ValidationErrorDetail(BaseModel):
    """
    Pydantic validation error detail.

    Provides structured information about validation failures.
    """

    loc: list[str | int] = Field(
        ...,
        description="Location of the error (field path)",
        examples=[["body", "email"], ["query", "limit"]],
    )

    msg: str = Field(
        ...,
        description="Error message",
        examples=["field required", "value is not a valid email address"],
    )

    type: str = Field(
        ...,
        description="Error type",
        examples=["value_error.missing", "value_error.email"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "loc": ["body", "email"],
                "msg": "value is not a valid email address",
                "type": "value_error.email",
            }
        }


class ValidationErrorResponse(BaseModel):
    """
    Validation error response for Pydantic validation failures.

    Returned when request validation fails (422 Unprocessable Entity).
    """

    error: ErrorDetail = Field(..., description="Error summary")
    validation_errors: list[ValidationErrorDetail] = Field(
        ..., description="Detailed validation errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                },
                "validation_errors": [
                    {
                        "loc": ["body", "email"],
                        "msg": "value is not a valid email address",
                        "type": "value_error.email",
                    }
                ],
            }
        }
