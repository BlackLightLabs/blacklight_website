"""
Log Sampling for High-Traffic Endpoints

Reduces log noise by sampling high-frequency requests (health checks, metrics, etc.)
while preserving error logs and important business events.
"""

import random
from typing import Set

from src.blacklight.common.settings import settings


class LogSampler:
    """
    Determine whether a request should be logged based on sampling configuration.

    High-traffic endpoints (health checks, metrics) are sampled at a lower rate,
    while errors and business-critical endpoints are always logged.
    """

    # Paths that should be sampled (not logged every time)
    SAMPLED_PATHS: Set[str] = {
        "/health",
        "/healthz",
        "/ready",
        "/metrics",
        "/ping",
        "/_health",
    }

    # Paths that should NEVER be sampled (always logged)
    ALWAYS_LOG_PATHS: Set[str] = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/logout",
        "/api/agents",  # Agent creation
    }

    # HTTP status codes that should ALWAYS be logged
    ALWAYS_LOG_STATUS_CODES: Set[int] = {
        400,  # Bad Request
        401,  # Unauthorized
        403,  # Forbidden
        404,  # Not Found
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }

    def __init__(self, sampling_rate: float | None = None):
        """
        Initialize log sampler.

        Args:
            sampling_rate: Probability of logging (0.0-1.0). Defaults to settings value.
        """
        self.sampling_rate = sampling_rate if sampling_rate is not None else settings.log_sampling_rate

    def should_log(
        self,
        path: str,
        method: str | None = None,
        status_code: int | None = None,
    ) -> bool:
        """
        Determine if a request should be logged.

        Args:
            path: Request path
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP response status code

        Returns:
            True if request should be logged, False otherwise
        """
        # Always log errors
        if status_code and status_code in self.ALWAYS_LOG_STATUS_CODES:
            return True

        # Always log critical paths
        if self._is_critical_path(path):
            return True

        # Sample high-traffic paths
        if path in self.SAMPLED_PATHS:
            return random.random() < self.sampling_rate

        # Log all other paths (normal traffic)
        return True

    def _is_critical_path(self, path: str) -> bool:
        """
        Check if path is business-critical and should always be logged.

        Args:
            path: Request path

        Returns:
            True if path is critical
        """
        # Exact match
        if path in self.ALWAYS_LOG_PATHS:
            return True

        # Prefix match for API paths
        critical_prefixes = (
            "/api/auth/",  # All auth operations
            "/api/admin/",  # All admin operations
        )

        return path.startswith(critical_prefixes)

    def get_sample_decision_metadata(self, path: str, decision: bool) -> dict[str, any]:
        """
        Get metadata about sampling decision for logging.

        Args:
            path: Request path
            decision: Whether request was logged

        Returns:
            Metadata dictionary
        """
        return {
            "sampled": not decision,  # True if request was NOT logged
            "sampling_rate": self.sampling_rate,
            "path_category": self._get_path_category(path),
        }

    def _get_path_category(self, path: str) -> str:
        """Categorize path for logging purposes."""
        if path in self.SAMPLED_PATHS:
            return "health_check"
        elif self._is_critical_path(path):
            return "critical"
        else:
            return "standard"


# Global instance
_sampler = LogSampler()


def should_log_request(path: str, method: str | None = None, status_code: int | None = None) -> bool:
    """
    Convenience function to check if request should be logged.

    Args:
        path: Request path
        method: HTTP method
        status_code: HTTP response status code

    Returns:
        True if request should be logged
    """
    return _sampler.should_log(path, method, status_code)
