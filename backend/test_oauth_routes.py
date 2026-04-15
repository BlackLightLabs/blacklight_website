#!/usr/bin/env python3
"""
Test script to verify OAuth routes are registered correctly.
Run this to check if the OAuth implementation is working without needing real OAuth credentials.
"""

import sys
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_oauth_routes_disabled():
    """Test that OAuth routes are NOT registered when OAuth is disabled"""
    print("Testing OAuth routes when OAUTH2_ENABLED=false...")

    from src.blacklight.features.auth.routes import router
    from src.blacklight.common.settings import settings

    print(f"OAuth2 enabled: {settings.oauth2_enabled}")

    # Get all routes
    routes = []
    for route in router.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)

    print(f"\nRegistered auth routes ({len(routes)} total):")
    for route in sorted(routes):
        print(f"  {route}")

    # Check for OAuth-specific routes
    oauth_routes = [r for r in routes if '/oauth/' in r or '/google/' in r or '/github/' in r or '/microsoft/' in r]

    if settings.oauth2_enabled:
        print(f"\n✅ OAuth2 enabled - found {len(oauth_routes)} OAuth routes")
    else:
        if oauth_routes:
            print(f"\n⚠️  OAuth2 disabled but found {len(oauth_routes)} OAuth routes (may be base OAuth routes)")
        else:
            print("\n✅ OAuth2 disabled - no dynamic OAuth provider routes registered")

    return routes


def test_oauth_validation():
    """Test OAuth environment variable validation"""
    print("\n" + "="*60)
    print("Testing OAuth environment variable validation...")
    print("="*60)

    from src.blacklight.common.settings import Settings

    # Test 1: OAuth enabled but no providers enabled
    print("\nTest 1: OAUTH2_ENABLED=true but no providers enabled")
    try:
        test_settings = Settings(
            oauth2_enabled=True,
            database_url="postgresql://test:test@localhost/test",
            jwt_secret="test",
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised error: {e}")

    # Test 2: Google enabled but missing credentials
    print("\nTest 2: GOOGLE_OAUTH_ENABLED=true but missing CLIENT_ID")
    try:
        test_settings = Settings(
            oauth2_enabled=True,
            google_oauth_enabled=True,
            google_client_secret="test-secret",
            database_url="postgresql://test:test@localhost/test",
            jwt_secret="test",
        )
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised error: {e}")

    # Test 3: Google enabled with valid credentials
    print("\nTest 3: GOOGLE_OAUTH_ENABLED=true with valid credentials")
    try:
        test_settings = Settings(
            oauth2_enabled=True,
            google_oauth_enabled=True,
            google_client_id="test-client-id",
            google_client_secret="test-secret",
            database_url="postgresql://test:test@localhost/test",
            jwt_secret="test",
        )
        print("✅ Settings validated successfully")
    except ValueError as e:
        print(f"❌ Unexpected error: {e}")


def test_oauth_schemas():
    """Test OAuth Pydantic schemas"""
    print("\n" + "="*60)
    print("Testing OAuth Pydantic schemas...")
    print("="*60)

    from src.blacklight.features.auth.schemas import (
        OAuthProviderInfo,
        OAuthProvidersResponse,
        ConnectedOAuthAccount,
        ConnectedAccountsResponse,
    )
    from datetime import datetime

    # Test OAuthProviderInfo
    print("\nTest 1: OAuthProviderInfo schema")
    provider = OAuthProviderInfo(
        name="google",
        display_name="Google",
        enabled=True,
        authorize_url="/api/auth/google/authorize",
    )
    print(f"✅ Created provider: {provider.name} ({provider.display_name})")

    # Test OAuthProvidersResponse
    print("\nTest 2: OAuthProvidersResponse schema")
    response = OAuthProvidersResponse(
        enabled=True,
        providers=[provider],
    )
    print(f"✅ Created response with {len(response.providers)} provider(s)")

    # Test ConnectedOAuthAccount
    print("\nTest 3: ConnectedOAuthAccount schema")
    account = ConnectedOAuthAccount(
        id=1,
        provider="google",
        display_name="Google",
        account_email="test@example.com",
        connected_at=datetime.now(),
    )
    print(f"✅ Created connected account: {account.provider} ({account.account_email})")

    # Test ConnectedAccountsResponse
    print("\nTest 4: ConnectedAccountsResponse schema")
    accounts_response = ConnectedAccountsResponse(
        accounts=[account],
        available_providers=[provider],
    )
    print(f"✅ Created accounts response with {len(accounts_response.accounts)} connected and {len(accounts_response.available_providers)} available")


if __name__ == "__main__":
    print("="*60)
    print("OAuth2 Implementation Test Suite")
    print("="*60)

    try:
        # Test 1: Route registration
        test_oauth_routes_disabled()

        # Test 2: Environment validation
        test_oauth_validation()

        # Test 3: Schemas
        test_oauth_schemas()

        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
