"""
Retry logic for transient failures

Provides decorators and utilities for retrying operations that may fail
due to transient errors (network issues, rate limits, temporary service outages).

Usage:
    @retry_on_transient_error(max_attempts=3, delay=1.0)
    async def call_external_api():
        # API call that may fail transiently
        ...

    @retry_on_db_error(max_attempts=5)
    async def query_database():
        # Database query that may fail due to connection issues
        ...
"""

import asyncio
import random
from functools import wraps
from typing import Any, Callable, Type

import structlog
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from src.blacklight.common.exceptions import DatabaseError, ExternalServiceError
from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.retry")


# Transient error types that should be retried
TRANSIENT_DB_ERRORS = (
    OperationalError,
    DisconnectionError,
    DBAPIError,
    SQLAlchemyTimeoutError,
)

TRANSIENT_NETWORK_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,  # Includes network-related errors
)


def calculate_backoff_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Uses exponential backoff: delay = base_delay * (2 ^ attempt)
    Adds jitter to prevent thundering herd problem.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with jitter
    """
    # Exponential backoff: 2^attempt * base_delay
    delay = min(base_delay * (2**attempt), max_delay)

    # Add random jitter (±25% of delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0, delay + jitter)


def retry_async(
    max_attempts: int | None = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable:
    """
    Decorator for retrying async functions on specified exceptions.

    Args:
        max_attempts: Maximum number of attempts (default from settings)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry (receives exception and attempt number)

    Returns:
        Decorated function

    Example:
        @retry_async(
            max_attempts=3,
            base_delay=1.0,
            exceptions=(ConnectionError, TimeoutError)
        )
        async def fetch_data():
            # May fail transiently
            ...
    """
    if max_attempts is None:
        max_attempts = settings.retry_max_attempts

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    # Try to execute the function
                    return await func(*args, **kwargs)

                except exceptions as exc:
                    last_exception = exc

                    # Don't retry on last attempt
                    if attempt == max_attempts - 1:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(exc),
                            error_type=type(exc).__name__,
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = calculate_backoff_delay(attempt, base_delay, max_delay)

                    # Log retry attempt
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        error=str(exc),
                        error_type=type(exc).__name__,
                        retry_delay=round(delay, 2),
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(exc, attempt + 1)

                    # Wait before retrying
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_on_db_error(
    max_attempts: int | None = None,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
) -> Callable:
    """
    Decorator for retrying database operations on transient errors.

    Retries on:
    - Connection errors
    - Timeouts
    - Operational errors (e.g., deadlocks)

    Args:
        max_attempts: Maximum retry attempts (default from settings)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Decorated function

    Example:
        @retry_on_db_error(max_attempts=5)
        async def get_user(user_id: int):
            async with SessionLocal() as session:
                result = await session.execute(...)
                return result.scalar_one_or_none()
    """

    def on_retry(exc: Exception, attempt: int) -> None:
        """Log database retry with context."""
        logger.warning(
            "database_retry",
            attempt=attempt,
            error_type=type(exc).__name__,
            error=str(exc),
        )

    return retry_async(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=TRANSIENT_DB_ERRORS,
        on_retry=on_retry,
    )


def retry_on_network_error(
    max_attempts: int | None = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Callable:
    """
    Decorator for retrying network/external service calls on transient errors.

    Retries on:
    - Connection errors
    - Timeouts
    - Network-related OS errors

    Args:
        max_attempts: Maximum retry attempts (default from settings)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Decorated function

    Example:
        @retry_on_network_error(max_attempts=3)
        async def call_llm_api(prompt: str):
            response = await llm.ainvoke(prompt)
            return response
    """

    def on_retry(exc: Exception, attempt: int) -> None:
        """Log network retry with context."""
        logger.warning(
            "network_retry",
            attempt=attempt,
            error_type=type(exc).__name__,
            error=str(exc),
        )

    return retry_async(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=TRANSIENT_NETWORK_ERRORS,
        on_retry=on_retry,
    )


def retry_on_llm_error(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> Callable:
    """
    Decorator for retrying LLM API calls on transient errors.

    Retries on:
    - Rate limit errors (429)
    - Server errors (5xx)
    - Network errors

    Uses longer delays than standard network retries since LLM APIs
    can be slower to recover.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay in seconds (higher for LLM)
        max_delay: Maximum delay in seconds

    Returns:
        Decorated function

    Example:
        @retry_on_llm_error(max_attempts=3)
        async def generate_agent_spec(prompt: str):
            response = await llm.ainvoke(prompt)
            return response.content
    """
    # LLM errors typically come from the LangChain/OpenAI SDK
    # We'll catch broad exceptions and let the circuit breaker handle persistent failures
    llm_errors = TRANSIENT_NETWORK_ERRORS + (Exception,)

    def on_retry(exc: Exception, attempt: int) -> None:
        """Log LLM retry with context."""
        logger.warning(
            "llm_retry",
            attempt=attempt,
            error_type=type(exc).__name__,
            error=str(exc),
        )

    return retry_async(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=llm_errors,
        on_retry=on_retry,
    )


async def retry_with_logging(
    func: Callable,
    max_attempts: int,
    operation_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Retry a function with structured logging.

    Utility function for one-off retry scenarios where you don't want
    to use a decorator.

    Args:
        func: Async function to retry
        max_attempts: Maximum attempts
        operation_name: Name for logging
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Example:
        result = await retry_with_logging(
            some_function,
            max_attempts=3,
            operation_name="fetch_agent",
            agent_id="abc123"
        )
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc

            if attempt == max_attempts - 1:
                logger.error(
                    "retry_exhausted",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                raise

            delay = calculate_backoff_delay(attempt, base_delay=1.0, max_delay=30.0)

            logger.warning(
                "retry_attempt",
                operation=operation_name,
                attempt=attempt + 1,
                max_attempts=max_attempts,
                error=str(exc),
                retry_delay=round(delay, 2),
            )

            await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
