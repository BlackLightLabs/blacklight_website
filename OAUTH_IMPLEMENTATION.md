# OAuth Implementation - Production-Ready Solution

## Overview

This document explains the **clean, battle-tested OAuth implementation** using FastAPI-Users with cookie-based authentication and custom `CookieRedirectTransport`. This follows the official FastAPI-Users patterns recommended by the maintainers.

## The Problem (What We Fixed)

### Previous Issues:
1. ❌ **redirect_url pointing to frontend** - OAuth provider redirected to frontend with code, but frontend never forwarded it back to backend
2. ❌ **Frontend intercepting OAuth flow** - Tried to fetch JSON and manually redirect (incorrect pattern)
3. ❌ **access_token KeyError** - OAuth code exchange failed due to improper flow
4. ❌ **No redirect after authentication** - Backend set cookie but returned 204 No Content instead of redirecting to frontend

## The Solution (CookieRedirectTransport Pattern)

### Correct OAuth Flow with Custom Transport:

```
1. User clicks "Continue with GitHub"
   ↓
2. Frontend redirects to: http://localhost:3000/api/auth/github/authorize
   ↓
3. Backend redirects to: https://github.com/login/oauth/authorize?client_id=...&redirect_uri=BACKEND_CALLBACK
   ↓
4. User authorizes on GitHub
   ↓
5. GitHub redirects to: http://localhost:3000/api/auth/github/callback?code=...
   ↓
6. Backend exchanges code for access token (token never exposed to frontend)
   ↓
7. Backend creates/logs in user
   ↓
8. CookieRedirectTransport sets httpOnly cookie AND returns RedirectResponse to frontend
   ↓
9. Browser redirects to: http://localhost:3000/oauth-success (with cookie already set)
   ↓
10. Frontend shows success message, invalidates user query, redirects home
   ↓
11. User is now authenticated (cookie set), can make authenticated requests
```

**Key Difference:** The `redirect_url` parameter is NOT used. Instead, GitHub redirects to the **backend callback**, which processes authentication and then uses `CookieRedirectTransport` to redirect to the frontend with the cookie already set.

## Key Implementation Details

### 1. Custom CookieRedirectTransport (backend/src/blacklight/features/auth/utils.py)

```python
class CookieRedirectTransport(CookieTransport):
    """
    Custom cookie transport that redirects to frontend after successful OAuth login.

    This is the recommended approach from FastAPI-Users maintainers.
    See: https://github.com/fastapi-users/fastapi-users/discussions/1173
    """

    async def get_login_response(self, token: str) -> Response:
        """Return redirect response to frontend after setting auth cookie."""
        response = RedirectResponse(
            url=f"{settings.frontend_url}/oauth-success",
            status_code=302
        )
        # Set the authentication cookie on the response
        self._set_login_cookie(response, token)
        return response

# Use custom transport
cookie_transport = CookieRedirectTransport(
    cookie_name="auth",
    cookie_max_age=settings.jwt_lifetime_seconds,
    cookie_httponly=True,
    cookie_secure=settings.is_production,
    cookie_samesite="strict" if settings.is_production else "lax",
)

# Authentication backend using custom transport
auth_backend = AuthenticationBackend(
    name="jwt-cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
```

### 2. Backend OAuth Router (backend/src/blacklight/features/auth/routes.py)

```python
# Dynamically register OAuth routers for enabled providers
if app_settings.oauth2_enabled:
    oauth_clients = get_enabled_oauth_clients()
    for provider_name, oauth_client in oauth_clients.items():
        router.include_router(
            fastapi_users.get_oauth_router(
                oauth_client,
                auth_backend,  # Uses CookieRedirectTransport
                app_settings.jwt_secret,
                # NO redirect_url parameter - defaults to backend callback
                # CookieRedirectTransport handles redirect to frontend
                is_verified_by_default=True,
                associate_by_email=True,
            ),
            prefix=f"/auth/{provider_name}",
            tags=["auth", "oauth"],
        )
```

**Key Parameters:**
- **NO `redirect_url`**: OAuth provider redirects to backend callback (default behavior)
- **`auth_backend`**: Uses `CookieRedirectTransport` which redirects to frontend after auth
- **`is_verified_by_default=True`**: Trust OAuth provider's email validation
- **`associate_by_email=True`**: Link OAuth account to existing user if email matches

### 3. Frontend OAuth Initiation (frontend/app/lib/auth-api.ts)

```typescript
/**
 * Initiate OAuth login flow for a provider (e.g., "google", "github")
 *
 * PRODUCTION PATTERN (Cookie-based auth):
 * 1. Frontend redirects to backend /authorize endpoint
 * 2. Backend redirects to OAuth provider (e.g., GitHub)
 * 3. User authorizes on provider's site
 * 4. Provider redirects to backend /callback with authorization code
 * 5. Backend exchanges code for token, creates/logs in user
 * 6. Backend sets httpOnly cookie and redirects to frontend success page
 * 7. Frontend now has auth cookie, can make authenticated requests
 *
 * This is the standard FastAPI-Users OAuth flow for cookie-based authentication.
 */
initiateOAuthLogin(provider: string): void {
  // Simply redirect to the backend's authorize endpoint
  // The backend handles the entire OAuth flow and sets the auth cookie
  window.location.href = `${API_BASE_URL}/api/auth/${provider}/authorize`;
}
```

**Why this is correct:**
- No fetch() call - just a simple redirect
- Backend handles entire OAuth flow
- Token exchange happens server-side (secure)
- httpOnly cookie set automatically
- No tokens exposed to frontend JavaScript

### 4. OAuth Success Page (frontend/app/routes/oauth-success.tsx)

```typescript
/**
 * OAuth Success Page
 *
 * This page is the redirect_url for OAuth flows.
 * After successful OAuth authentication, the backend redirects here.
 * The httpOnly auth cookie has already been set by the backend.
 */
export default function OAuthSuccess() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    toast.success("Successfully logged in!");
    queryClient.invalidateQueries({ queryKey: ["user"] });

    const timer = setTimeout(() => {
      navigate("/", { replace: true });
    }, 1000);

    return () => clearTimeout(timer);
  }, [navigate, queryClient]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Successfully logged in!</h1>
        <p className="text-muted-foreground mt-2">Redirecting you to the app...</p>
      </div>
    </div>
  );
}
```

## Required GitHub OAuth App Configuration

### Authorization callback URL:
```
http://localhost:3000/api/auth/github/callback
```

**CRITICAL:** The callback URL must point to the **backend** callback endpoint (proxied through Nginx), NOT a frontend route.

### Callback URL Configuration:
- **Callback URL** (GitHub OAuth App): Where GitHub sends the authorization code → Must be backend endpoint
- **Frontend Redirect**: Handled by `CookieRedirectTransport` after authentication completes

## Environment Configuration

### Backend (.env)
```bash
# Frontend URL for OAuth redirects (Nginx proxy)
FRONTEND_URL=http://localhost:3000

# GitHub OAuth2
GITHUB_OAUTH_ENABLED=true
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
```

### Frontend (.env)
```bash
# Backend API URL (Nginx proxy)
VITE_API_URL=http://localhost:3000
```

## Why This Pattern is Production-Ready

✅ **Follows FastAPI-Users official patterns** - Recommended by maintainers (Discussion #1173)
✅ **Secure token handling** - Tokens never exposed to frontend JavaScript
✅ **httpOnly cookies** - Protected against XSS attacks
✅ **SameSite=lax** - CSRF protection while allowing OAuth redirects
✅ **No CORS issues** - Same-origin via Nginx proxy
✅ **Account association** - Automatically links OAuth to existing users by email
✅ **Auto-verification** - Trusts OAuth provider's email validation
✅ **Provider-agnostic** - Works with ALL OAuth providers (Google, GitHub, Microsoft, OIDC)
✅ **Clean separation** - Backend handles auth, frontend handles UX

## Common Pitfalls (What NOT to Do)

❌ **Don't fetch() the authorize endpoint** - It returns a redirect, not JSON
❌ **Don't try to handle OAuth in frontend** - Backend must exchange code for token
❌ **Don't expose access tokens** - Keep them server-side only
❌ **Don't configure callback to frontend** - GitHub must callback to backend
❌ **Don't use redirect_url parameter** - Let it default to None and use CookieRedirectTransport instead
❌ **Don't modify response in on_after_login** - Use custom transport class instead

## Testing the Flow

1. **Start services:**
   ```bash
   # Backend (from backend/)
   uv run uvicorn src.blacklight.main:app --reload --host 0.0.0.0 --port 8000

   # Frontend (from frontend/)
   npm run dev

   # Nginx (from root/)
   docker compose up nginx
   ```

2. **Update GitHub OAuth App:**
   - Authorization callback URL: `http://localhost:3000/api/auth/github/callback`

3. **Test OAuth flow:**
   - Navigate to: http://localhost:3000/login
   - Click "Continue with GitHub"
   - Authorize on GitHub
   - Should redirect to http://localhost:3000/oauth-success
   - Should see success message and redirect to home
   - User should be logged in (check user menu in top right)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                       │
│                   http://localhost:3000                      │
│                                                              │
│  / → Frontend (React Router, Vite)                          │
│  /api → Backend (FastAPI)                                   │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌─────────────────┐              ┌──────────────────┐
│    Frontend     │              │     Backend      │
│  localhost:5173 │              │  localhost:8000  │
│                 │              │                  │
│ • OAuth button  │              │ • OAuth router   │
│ • Redirects to  │              │ • Code exchange  │
│   backend       │              │ • Set cookie     │
│ • Success page  │              │ • Redirect user  │
└─────────────────┘              └──────────────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │  PostgreSQL DB   │
                                 │ • users table    │
                                 │ • oauth_accounts │
                                 └──────────────────┘
```

## Database Schema

### oauth_accounts table:
```sql
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    oauth_name VARCHAR(100) NOT NULL,  -- "github", "google", etc.
    account_id VARCHAR(320) NOT NULL,   -- Provider's user ID
    account_email VARCHAR(320) NOT NULL,
    access_token TEXT,                  -- Stored securely server-side
    refresh_token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## References

- [FastAPI-Users OAuth Configuration](https://fastapi-users.github.io/fastapi-users/latest/configuration/oauth/)
- [CookieRedirectTransport Pattern - Discussion #1173](https://github.com/fastapi-users/fastapi-users/discussions/1173) - **Recommended approach**
- [Google OAuth with React - Discussion #1366](https://github.com/fastapi-users/fastapi-users/discussions/1366)
- [OAuth Callback Handling - Issue #434](https://github.com/fastapi-users/fastapi-users/issues/434)

## Implementation Checklist

1. ✅ Created `CookieRedirectTransport` class in `utils.py`
2. ✅ Backend OAuth router configured WITHOUT redirect_url parameter
3. ✅ Frontend OAuth flow uses direct redirect to backend
4. ✅ OAuth success page created at `/oauth-success`
5. ✅ GitHub OAuth app callback URL configured
6. ✅ Tested complete OAuth flow end-to-end with GitHub
7. ✅ OAuth account management in settings page
8. 🔄 Ready to add additional providers (Google, Microsoft, OIDC)
