"""
Auth feature utilities

Provides authentication backend configuration for FastAPI-Users including:
- JWT strategy configuration
- Cookie transport configuration
- Authentication backend setup
"""

from fastapi import Response
from fastapi.responses import RedirectResponse
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

from src.blacklight.common.settings import settings


def get_jwt_strategy() -> JWTStrategy:
    """
    Get JWT strategy for token generation and validation

    Returns:
        JWTStrategy configured with secret and lifetime from centralized settings
    """
    return JWTStrategy(secret=settings.jwt_secret, lifetime_seconds=settings.jwt_lifetime_seconds)


class CookieRedirectTransport(CookieTransport):
    """
    Custom cookie transport that redirects to frontend after successful OAuth login.

    This transport extends the standard CookieTransport to return a redirect response
    to the frontend after setting the authentication cookie. This is the recommended
    approach for handling OAuth flows with a separate frontend application.

    See: https://github.com/fastapi-users/fastapi-users/discussions/1173
    """

    async def get_login_response(self, token: str) -> Response:
        """
        Override to return redirect response to frontend after setting auth cookie.

        Args:
            token: JWT token to set in cookie

        Returns:
            RedirectResponse to frontend OAuth success page with auth cookie set
        """
        # Create redirect response to frontend
        response = RedirectResponse(
            url=f"{settings.frontend_url}/oauth-success",
            status_code=302
        )

        # Set the authentication cookie on the response
        self._set_login_cookie(response, token)

        return response


# Cookie transport configuration
# httpOnly=True prevents JavaScript access (XSS protection)
# secure=True enforces HTTPS (should be True in production)
# samesite: "lax" in dev (allows OAuth redirects), "strict" in prod (max security)
cookie_transport = CookieRedirectTransport(
    cookie_name="auth",
    cookie_max_age=settings.jwt_lifetime_seconds,
    cookie_httponly=True,
    cookie_secure=settings.is_production,  # Only True in production
    cookie_samesite="strict" if settings.is_production else "lax",  # "lax" for cross-origin OAuth in dev
)

# Authentication backend combining cookie transport with JWT strategy
auth_backend = AuthenticationBackend(
    name="jwt-cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
