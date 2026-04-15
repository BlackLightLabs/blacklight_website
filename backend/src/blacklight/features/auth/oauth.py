"""
OAuth2 Client Factory

Provides factory functions for creating OAuth2 client instances for different providers.
Clients are created dynamically based on environment configuration.

Supported providers:
- Google OAuth2
- Microsoft Graph OAuth2
- GitHub OAuth2
- Generic OIDC (OpenID Connect)
"""

from typing import Any
from contextlib import asynccontextmanager

import httpx
from httpx_oauth.clients.github import GitHubOAuth2
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.microsoft import MicrosoftGraphOAuth2
from httpx_oauth.clients.openid import OpenID

from src.blacklight.common.settings import settings


class GitHubOAuth2JSON(GitHubOAuth2):
    """
    Custom GitHub OAuth2 client that requests JSON token responses.

    GitHub's token endpoint returns application/x-www-form-urlencoded by default,
    but httpx-oauth expects JSON. This client adds the Accept: application/json
    header to all requests to ensure GitHub returns JSON.

    See: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#response
    """

    @asynccontextmanager
    async def get_httpx_client(self):
        """Override to add Accept: application/json header to all requests."""
        async with httpx.AsyncClient(
            headers={"Accept": "application/json"}
        ) as client:
            yield client


def get_google_oauth_client() -> GoogleOAuth2 | None:
    """
    Get Google OAuth2 client if enabled.

    Returns:
        GoogleOAuth2 client or None if disabled
    """
    if not settings.google_oauth_enabled:
        return None

    if not settings.google_client_id or not settings.google_client_secret:
        return None

    return GoogleOAuth2(
        settings.google_client_id,
        settings.google_client_secret,
    )


def get_github_oauth_client() -> GitHubOAuth2JSON | None:
    """
    Get GitHub OAuth2 client if enabled.

    Uses custom GitHubOAuth2JSON client that requests JSON token responses
    instead of GitHub's default application/x-www-form-urlencoded format.

    Returns:
        GitHubOAuth2JSON client or None if disabled
    """
    if not settings.github_oauth_enabled:
        return None

    if not settings.github_client_id or not settings.github_client_secret:
        return None

    return GitHubOAuth2JSON(
        settings.github_client_id,
        settings.github_client_secret,
    )


def get_microsoft_oauth_client() -> MicrosoftGraphOAuth2 | None:
    """
    Get Microsoft Graph OAuth2 client if enabled.

    Returns:
        MicrosoftGraphOAuth2 client or None if disabled
    """
    if not settings.microsoft_oauth_enabled:
        return None

    if not settings.microsoft_client_id or not settings.microsoft_client_secret:
        return None

    return MicrosoftGraphOAuth2(
        settings.microsoft_client_id,
        settings.microsoft_client_secret,
        tenant=settings.microsoft_tenant,
    )


def get_oidc_oauth_client() -> OpenID | None:
    """
    Get generic OIDC (OpenID Connect) client if enabled.

    Returns:
        OpenID client or None if disabled
    """
    if not settings.oidc_enabled:
        return None

    if not all([
        settings.oidc_client_id,
        settings.oidc_client_secret,
        settings.oidc_well_known_url,
    ]):
        return None

    return OpenID(
        settings.oidc_client_id,
        settings.oidc_client_secret,
        settings.oidc_well_known_url,
        name=settings.oidc_provider_name,
    )


def get_enabled_oauth_clients() -> dict[str, Any]:
    """
    Get all enabled OAuth2 clients.

    Returns dict of enabled OAuth clients for dynamic router generation.
    Keys are provider names (lowercase), values are OAuth client instances.

    Returns:
        Dict mapping provider names to OAuth client instances
    """
    clients: dict[str, Any] = {}

    if google := get_google_oauth_client():
        clients["google"] = google

    if github := get_github_oauth_client():
        clients["github"] = github

    if microsoft := get_microsoft_oauth_client():
        clients["microsoft"] = microsoft

    if oidc := get_oidc_oauth_client():
        clients[settings.oidc_provider_name.lower()] = oidc

    return clients


def get_enabled_provider_names() -> list[str]:
    """
    Get list of enabled OAuth provider names.

    Returns:
        List of enabled provider names (e.g., ["google", "github"])
    """
    return list(get_enabled_oauth_clients().keys())
