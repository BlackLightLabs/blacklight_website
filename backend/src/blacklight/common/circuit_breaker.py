"""
Circuit breaker pattern for external service calls

Prevents cascading failures when external services (like LLM APIs) are down
by temporarily blocking requests after a threshold of failures.

Circuit States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests are blocked
- HALF_OPEN: Testing if service has recovered

Usage:
    circuit_breaker = CircuitBreaker(
        name="openai_llm",
        failure_threshold=5,
        recovery_timeout=60.0
    )

    @circuit_breaker.call
    async def call_llm():
        # LLM API call
        ...
"""

import asyncio
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable

import structlog

from src.blacklight.common.exceptions import CircuitBreakerOpenError
from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.circuit_breaker")

# OpenTelemetry metrics for circuit breaker
try:
    from src.blacklight.common.otel import (
        circuit_breaker_closed_counter,
        circuit_breaker_failures_counter,
        circuit_breaker_opened_counter,
        circuit_breaker_state_gauge,
        circuit_breaker_successes_counter,
    )

    METRICS_ENABLED = True
except ImportError:
    # Metrics module not available yet (during initial import)
    METRICS_ENABLED = False


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Tracks failures and opens circuit when threshold is exceeded,
    preventing further calls until recovery timeout expires.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold or settings.circuit_breaker_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = asyncio.Lock()

        # Initialize metrics
        if METRICS_ENABLED:
            self._update_state_metric()

        logger.info(
            "circuit_breaker_initialized",
            name=name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self._state == CircuitState.CLOSED

    def _update_state_metric(self) -> None:
        """Update OpenTelemetry metric for circuit breaker state."""
        if not METRICS_ENABLED:
            return

        # Map state to numeric value
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2,
        }.get(self._state, 0)

        # OpenTelemetry: Use add() to set the gauge value
        # Note: For gauges, we need to track the delta, not absolute value
        # For state tracking, we'll use the value directly
        circuit_breaker_state_gauge.add(state_value, {"service": self.name})

    async def _should_attempt_reset(self) -> bool:
        """
        Check if circuit should attempt recovery.

        Returns True if recovery timeout has elapsed.
        """
        if self._state != CircuitState.OPEN:
            return False

        time_since_failure = time.time() - self._last_failure_time
        return time_since_failure >= self.recovery_timeout

    async def _record_success(self) -> None:
        """Record successful call and potentially close circuit."""
        async with self._lock:
            # Track success in metrics
            if METRICS_ENABLED:
                circuit_breaker_successes_counter.add(1, {"service": self.name})

            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open state means service recovered
                self._state = CircuitState.CLOSED
                self._failure_count = 0

                # Update metrics
                if METRICS_ENABLED:
                    self._update_state_metric()
                    circuit_breaker_closed_counter.add(1, {"service": self.name})

                logger.info(
                    "circuit_breaker_closed",
                    name=self.name,
                    message="Service recovered, circuit closed",
                )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
                    logger.debug(
                        "circuit_breaker_reset",
                        name=self.name,
                        message="Failure count reset after success",
                    )

    async def _record_failure(self, exception: Exception) -> None:
        """
        Record failed call and potentially open circuit.

        Args:
            exception: The exception that occurred
        """
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            # Track failure in metrics
            if METRICS_ENABLED:
                circuit_breaker_failures_counter.add(1, {"service": self.name})

            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open state means service still down
                self._state = CircuitState.OPEN

                # Update metrics
                if METRICS_ENABLED:
                    self._update_state_metric()
                    circuit_breaker_opened_counter.add(1, {"service": self.name})

                logger.warning(
                    "circuit_breaker_reopened",
                    name=self.name,
                    error=str(exception),
                    message="Service still failing, circuit reopened",
                )

            elif self._failure_count >= self.failure_threshold:
                # Threshold exceeded, open circuit
                self._state = CircuitState.OPEN

                # Update metrics
                if METRICS_ENABLED:
                    self._update_state_metric()
                    circuit_breaker_opened_counter.add(1, {"service": self.name})

                logger.error(
                    "circuit_breaker_opened",
                    name=self.name,
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                    error=str(exception),
                    message="Failure threshold exceeded, circuit opened",
                )

            else:
                # Still under threshold
                logger.warning(
                    "circuit_breaker_failure",
                    name=self.name,
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                    error=str(exception),
                )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception if call fails
        """
        # Check if we should attempt recovery
        if await self._should_attempt_reset():
            async with self._lock:
                self._state = CircuitState.HALF_OPEN

                # Update metrics
                if METRICS_ENABLED:
                    self._update_state_metric()

                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    message="Testing service recovery",
                )

        # Block request if circuit is open
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                message=f"Circuit breaker '{self.name}' is open. Service temporarily unavailable.",
                service_name=self.name,
                details={
                    "failure_count": self._failure_count,
                    "threshold": self.failure_threshold,
                    "recovery_timeout": self.recovery_timeout,
                    "time_until_retry": max(
                        0,
                        self.recovery_timeout
                        - (time.time() - self._last_failure_time),
                    ),
                },
            )

        # Try to execute function
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result

        except self.expected_exception as exc:
            await self._record_failure(exc)
            raise

    def __call__(self, func: Callable) -> Callable:
        """
        Use circuit breaker as a decorator.

        Example:
            circuit = CircuitBreaker(name="llm_api")

            @circuit
            async def call_llm():
                ...
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.call(func, *args, **kwargs)

        return wrapper

    async def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0

            # Update metrics
            if METRICS_ENABLED:
                self._update_state_metric()
                circuit_breaker_closed_counter.add(1, {"service": self.name})

            logger.info("circuit_breaker_manually_reset", name=self.name)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with current state and metrics
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self._last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers for common services
# These are initialized lazily when first accessed

_llm_circuit_breaker: CircuitBreaker | None = None


def get_llm_circuit_breaker() -> CircuitBreaker:
    """
    Get or create the LLM circuit breaker.

    Returns:
        CircuitBreaker instance for LLM calls
    """
    global _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        _llm_circuit_breaker = CircuitBreaker(
            name="llm_api",
            failure_threshold=settings.circuit_breaker_threshold,
            recovery_timeout=60.0,  # 1 minute recovery timeout for LLM
            expected_exception=Exception,  # Catch all LLM errors
        )
    return _llm_circuit_breaker


async def reset_all_circuit_breakers() -> None:
    """Reset all global circuit breakers. Useful for testing."""
    global _llm_circuit_breaker
    if _llm_circuit_breaker:
        await _llm_circuit_breaker.reset()
    logger.info("all_circuit_breakers_reset")
