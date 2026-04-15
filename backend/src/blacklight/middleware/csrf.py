"""
CSRF Protection Middleware

Implements double-submit cookie pattern for CSRF protection.
"""

import secrets

from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware using double-submit cookie pattern

    This middleware:
    1. Generates a CSRF token and sets it as a non-httpOnly cookie
    2. Requires the same token to be sent in a header for state-changing requests
    3. Validates that cookie and header tokens match
    """

    def __init__(
        self,
        app: ASGIApp,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        safe_methods: tuple = ("GET", "HEAD", "OPTIONS", "TRACE"),
        cookie_secure: bool = False,
        cookie_samesite: str = "strict",
    ):
        """
        Initialize CSRF middleware

        Args:
            app: ASGI application
            cookie_name: Name of the CSRF cookie
            header_name: Name of the CSRF header
            safe_methods: HTTP methods that don't require CSRF protection
            cookie_secure: Whether to set Secure flag on cookie
            cookie_samesite: SameSite attribute for cookie
        """
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.safe_methods = safe_methods
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply CSRF protection

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with CSRF cookie set

        Raises:
            HTTPException: If CSRF validation fails
        """
        # Get or generate CSRF token
        csrf_token = request.cookies.get(self.cookie_name)

        if not csrf_token:
            # Generate new token if none exists
            csrf_token = secrets.token_urlsafe(32)

        # For state-changing requests, validate CSRF token
        if request.method not in self.safe_methods:
            # Check if token is present in header
            header_token = request.headers.get(self.header_name)

            if not header_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing in header"
                )

            # Validate that cookie and header tokens match
            if not secrets.compare_digest(csrf_token, header_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch"
                )

        # Process request
        response: Response = await call_next(request)

        # Set CSRF cookie in response (refresh on every request)
        response.set_cookie(
            key=self.cookie_name,
            value=csrf_token,
            httponly=False,  # Must be accessible to JavaScript
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            max_age=86400,  # 24 hours
        )

        return response
