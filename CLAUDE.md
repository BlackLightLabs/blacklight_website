# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Agent Builder** is a conversational AI platform that lets users create custom LangGraph agents through natural language. Users describe what they want, and an AI assistant asks clarifying questions to generate a fully functional agent without writing code.

### Local AI Inference
The project supports a **local AI inference server via LMStudio** running at `http://localhost:1234/v1`. This allows development and testing without relying solely on cloud-based LLM providers.

## Tech Stack

- **Frontend**: React Router v7, TypeScript, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python 3.10+, LangChain, LangGraph, SQLAlchemy, PostgreSQL
- **Package Managers**: npm (frontend), **uv** (backend - fast Rust-based Python package manager)
- **Database**: PostgreSQL with Alembic migrations

## Development Commands

### Docker (from project root)
```bash
# Start PostgreSQL database
docker compose up -d postgres

# Stop database
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v

# View logs
docker compose logs -f postgres

# Database setup script (starts DB + runs migrations)
cd backend && ./scripts/setup-db.sh
```

### Frontend (from `/frontend`)
```bash
# Install dependencies
npm install

# Start development server (Vite)
npm run dev

# Build for production
npm run build

# Run type checking
npm run typecheck

# Run unit tests
npm run test

# Run unit tests once
npm run test:run

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui
```

### Backend (from `/backend`)

**Important**: All Python commands use the `uv` package manager.

```bash
# Install/sync dependencies from lockfile
uv sync

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Start development server with auto-reload
uv run uvicorn src.blacklight.main:app --reload --host 0.0.0.0 --port 8000

# Run Python scripts
uv run python script.py

# Run tests
uv run pytest

# Run specific test file
uv run pytest src/blacklight/features/agents/tests/test_repositories.py

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Database migrations
uv run alembic upgrade head                              # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create new migration
uv run alembic downgrade -1                              # Rollback one migration

# Create database (if needed)
createdb agent_builder
```

## Architecture

### Project Structure

The backend uses a **feature-based architecture** (also called modular monolith pattern) where code is organized by business domain rather than technical layer:

```
backend/src/blacklight/
├── common/                    # Shared infrastructure
│   ├── base_repository.py    # Base model and repository classes
│   ├── database.py           # Database session management
│   └── llm_config.py         # Multi-provider LLM configuration
│
├── features/                  # Feature modules
│   ├── auth/                 # Authentication & authorization
│   │   ├── models.py         # User, Role, Permission, AuditLog models
│   │   ├── repositories.py   # UserRepository, RoleRepository, etc.
│   │   ├── services.py       # AuthService, PermissionService
│   │   ├── routes.py         # Auth & settings API endpoints
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── utils.py          # JWT, cookie config
│   │   └── dependencies.py   # DI providers for auth services
│   │
│   ├── agents/               # Agent creation & management
│   │   ├── models.py         # Agent, Conversation, Message models
│   │   ├── repositories.py   # AgentRepository, ConversationRepository
│   │   ├── services.py       # AgentBuilderService
│   │   ├── routes.py         # Agent API endpoints
│   │   ├── schemas.py        # Agent request/response schemas
│   │   ├── dependencies.py   # DI providers for agent services
│   │   └── tests/            # Unit, integration, and system tests
│   │       ├── test_repositories.py
│   │       ├── test_services.py
│   │       ├── test_api_endpoints.py
│   │       └── test_agent_flow.py
│   │
│   └── executions/           # Agent execution tracking
│       ├── models.py         # Execution model
│       ├── repositories.py   # ExecutionRepository
│       ├── services.py       # AgentExecutionService
│       ├── schemas.py        # Execution request/response schemas
│       └── dependencies.py   # DI providers for execution services
│
├── dependencies/             # Global dependencies
│   ├── database.py          # get_db() provider
│   └── permissions.py       # RBAC permission checkers
│
├── main.py                  # FastAPI app initialization
└── conftest.py             # Pytest fixtures (at backend root)
```

**Key Principles**:
- **Absolute imports only**: All imports use `from src.blacklight.features...` (never relative)
- **Feature encapsulation**: Each feature contains all its models, repos, services, routes, and tests
- **Shared code in common/**: Database, LLM config, and base classes live in `common/`
- **Tests colocated**: Tests live in `features/*/tests/` next to the code they test
- **Clear boundaries**: Features communicate through well-defined service interfaces

**Benefits**:
- Easier to understand what code belongs to which feature
- Simpler to test features in isolation
- Reduced risk of circular dependencies
- Natural path for future microservices extraction if needed

### High-Level Flow
1. **User initiates conversation** → Frontend sends message via SSE streaming endpoint
2. **Backend creates/retrieves conversation** → Stores in PostgreSQL via repositories
3. **LLM streams response** → Uses StreamingCallbackHandler to buffer tokens
4. **Agent specification extracted** → When LLM outputs "AGENT_READY:" with JSON
5. **LangGraph workflow compiled** → Agent persisted with READY status
6. **Agent execution** → Future feature for running created agents

### Key Architectural Patterns

#### Repository Pattern
All database operations go through repositories, not direct SQLAlchemy access in routes:
- `features/agents/repositories.py` - `AgentRepository`, `ConversationRepository`
- `features/executions/repositories.py` - `ExecutionRepository`
- `features/auth/repositories.py` - `UserRepository`, `RoleRepository`, `PermissionRepository`, `AuditLogRepository`, `UserSettingsRepository`

**Why**: Separates data access from business logic, makes testing easier, allows swapping data sources.

**Async Pattern**: All repositories use `AsyncSession` and async/await:
```python
async def get_by_id(self, id: int) -> Optional[ModelType]:
    stmt = select(self.model).where(self.model.id == id)
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

#### Service Layer
Business logic lives in services, not route handlers:
- `features/agents/services.py` - `AgentBuilderService` (conversational agent creation, streaming)
- `features/executions/services.py` - `AgentExecutionService` (agent execution tracking)
- `features/auth/services.py` - `AuthService`, `PermissionService` (authentication, RBAC)

**Why**: Routes stay thin, services can be reused, business logic is testable independently. All services are fully async-compatible.

#### Dependency Injection
FastAPI's `Depends()` provides database sessions and services to routes:
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency"""
    async with async_session_maker() as session:
        yield session

async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Get authenticated user from cookie"""
    # Provided by FastAPI-Users
    pass

def get_agent_builder_service(db: AsyncSession = Depends(get_db)) -> AgentBuilderService:
    """Create agent builder service with database session"""
    return AgentBuilderService(db)
```

**Why**: Loose coupling, easy to mock for tests, clear dependency graph. All dependencies are async-compatible.

#### Streaming with Server-Sent Events (SSE)
Real-time token streaming uses:
1. `StreamingCallbackHandler` (backend) - Buffers tokens in asyncio.Queue
2. `EventSourceResponse` (FastAPI) - Sends SSE events
3. `EventSource` API (frontend) - Receives and parses events

**Why**: ChatGPT-style UX, immediate feedback, better perceived performance.

#### Authentication & RBAC
The application uses **FastAPI-Users** for authentication with cookie-based sessions and a custom RBAC system:

**Authentication Flow**:
1. User registration via `/api/auth/register` (POST) - creates user account
2. Login via `/api/auth/login` (POST) - sets httpOnly cookie with JWT
3. Protected routes use `current_active_user` dependency to verify authentication
4. Logout via `/api/auth/logout` (POST) - clears auth cookie

**RBAC Components**:
- **Roles**: Named sets of permissions (e.g., "admin", "user", "viewer")
- **Permissions**: Granular access control (resource:action pairs like "agents:create", "agents:delete")
- **Role Assignment**: Users are assigned one role, inheriting all its permissions
- **Permission Checks**: `PermissionService.check_permission()` validates user access

**Audit Logging**:
All security events are logged to the `audit_logs` table:
- User registration and login attempts (success/failure)
- Permission grants and revocations
- Role assignments
- Sensitive data access

The project uses a **DRY audit logging system** with two complementary patterns:

1. **Route-Level Audit Logging** (Dependency Injection Pattern):
   ```python
   from src.blacklight.common.audit import AuditLog

   @router.post("/agents")
   async def create_agent(
       user: User = Depends(RequirePermission("agents:create")),
       _audit: None = Depends(AuditLog("agent_management", "agent_created"))
   ):
       # Audit log is automatically created when route completes
       ...
   ```

2. **Service-Level Audit Logging** (Decorator Pattern):
   ```python
   from src.blacklight.common.audit import audit_log

   @audit_log("role_management", "role_assigned", user_id_param="user_id", include_args=True)
   async def assign_role(self, user_id: int, role_name: str) -> User | None:
       # Audit log is automatically created when method completes
       ...
   ```

**Benefits of DRY Audit Logging**:
- ✅ Automatic request context extraction (IP address, user agent)
- ✅ No repetitive `audit_repo.log_event()` calls
- ✅ Consistent audit trail across all features
- ✅ Easy to add to new endpoints/services
- ✅ Type-safe and fully async-compatible

**Manual Logging** (when needed):
```python
from src.blacklight.common.audit import log_audit_event

await log_audit_event(
    db=db,
    event_type="custom_event",
    event_action="custom_action",
    user_id=user.id,
    details={"key": "value"}
)
```

**Key Files**:
- `backend/src/blacklight/common/audit.py` - Audit utilities (AuditLog, @audit_log, helpers)
- `backend/src/blacklight/middleware/audit_context.py` - Middleware for ContextVars
- `backend/src/blacklight/features/auth/` - Complete auth feature module
- `backend/src/blacklight/features/auth/services.py` - `AuthService`, `PermissionService`
- `backend/src/blacklight/features/auth/routes.py` - Auth endpoints, `current_active_user`
- `backend/src/blacklight/features/auth/models.py` - User, Role, Permission, AuditLog
- `backend/src/blacklight/dependencies/permissions.py` - Permission check decorators

**Why**: Secure user isolation, multi-tenant ready, audit trail for compliance, DRY code.

#### User Settings & Theming
User preferences persist to the database via the `user_settings` table:

**Settings Features**:
- **Theme Preference**: Light, dark, or system (synced to localStorage for instant apply)
- **Custom Prompts**: Override default system prompts and agent instructions
- **Preferences JSON**: Extensible key-value store for future settings

**Dark Mode Implementation**:
1. `ThemeProvider` component wraps app in `root.tsx`
2. Theme stored in both localStorage (client) and database (persistence)
3. SSR-safe: checks `typeof window !== "undefined"` before localStorage access
4. System theme detection via `window.matchMedia("(prefers-color-scheme: dark)")`
5. All shadcn/ui components respond to `.dark` class on `<html>` root

**API Endpoints**:
- `GET /api/settings/me` - Get current user's settings
- `PATCH /api/settings/me` - Update settings (custom_prompts, preferences)
- `PATCH /api/settings/me/theme` - Quick theme update

**Key Files**:
- `frontend/app/components/theme-provider.tsx` - Theme context and localStorage sync
- `frontend/app/components/mode-toggle.tsx` - Theme switcher dropdown
- `frontend/app/routes/settings.tsx` - Settings page UI
- `frontend/app/lib/settings-api.ts` - Settings API client
- `backend/src/blacklight/features/auth/models.py` - UserSettings model
- `backend/src/blacklight/features/auth/routes.py` - Settings endpoints

**Why**: Personalized UX, persistent across sessions, accessibility (dark mode reduces eye strain).

#### OAuth2 Social Login
The application supports **OAuth2 social login** with multiple providers, allowing users to authenticate using their existing accounts:

**Supported Providers**:
- **Google OAuth2** - Login with Google accounts
- **GitHub OAuth2** - Login with GitHub accounts
- **Microsoft OAuth2** - Login with Microsoft/Azure AD accounts
- **Generic OIDC** - Support for Auth0, Okta, Keycloak, and other OIDC providers

**Key Features**:
- ✅ Multiple provider support with dynamic configuration
- ✅ Account linking - users can connect multiple OAuth providers to one account
- ✅ Connected Accounts UI - manage OAuth connections in settings page
- ✅ Environment validation - validates credentials at startup
- ✅ Safe disconnect - prevents users from removing last authentication method
- ✅ Dynamic UI - OAuth buttons appear/disappear based on configuration

**Quick Setup**:
```bash
# In backend/.env
OAUTH2_ENABLED=true
FRONTEND_URL=http://localhost:5173

# For GitHub (easiest for local testing)
GITHUB_OAUTH_ENABLED=true
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Apply migration
uv run alembic upgrade head
```

**OAuth Flow**:
1. User clicks OAuth button → Frontend redirects to `/api/auth/{provider}/authorize`
2. Backend redirects to provider authorization page
3. User authorizes application
4. Provider redirects back to `/api/auth/{provider}/callback`
5. FastAPI-Users exchanges code for tokens, creates/links user account
6. `CookieRedirectTransport` sets httpOnly authentication cookie
7. Backend redirects to frontend `/oauth-success` with cookie already set
8. Frontend redirects to home page - user is logged in!

**API Endpoints**:
- `GET /api/auth/oauth/providers` - List enabled providers (public)
- `GET /api/auth/{provider}/authorize` - Initiate OAuth flow (public)
- `GET /api/auth/{provider}/callback` - OAuth callback handler (public)
- `GET /api/auth/oauth/accounts` - List connected accounts (protected)
- `DELETE /api/auth/oauth/accounts/{id}` - Disconnect account (protected)

**Connected Accounts Management**:
Users can view and manage their OAuth connections in the Settings page:
- View all connected OAuth providers with emails and connection dates
- See available providers to connect
- Link additional OAuth providers to the same account
- Disconnect OAuth accounts (safety check: must have password or another OAuth account)

**Testing OAuth Locally**:
```bash
# Run automated tests (no OAuth credentials needed)
cd backend
uv run python test_oauth_routes.py        # Validation and schemas
uv run python test_oauth_integration.py   # API endpoints

# For full manual testing with real providers:
# 1. Set up OAuth app in provider console (GitHub easiest)
# 2. Configure credentials in .env
# 3. Start backend and frontend
# 4. Test login flow in browser
```

**Key Files**:
- `backend/src/blacklight/common/settings.py` - OAuth configuration with validation
- `backend/src/blacklight/features/auth/oauth.py` - OAuth client factory
- `backend/src/blacklight/features/auth/routes.py` - OAuth endpoints
- `backend/src/blacklight/features/auth/utils.py` - `CookieRedirectTransport` for OAuth redirects
- `backend/src/blacklight/features/auth/models.py` - OAuthAccount model
- `backend/alembic/versions/df9eb5ec316d_add_oauth_accounts_table.py` - Migration
- `frontend/app/components/oauth-button.tsx` - OAuth button component
- `frontend/app/components/login-form.tsx` - OAuth integration
- `frontend/app/routes/oauth-success.tsx` - OAuth success page (redirect target)
- `frontend/app/routes/settings.tsx` - Connected Accounts UI

**Environment Variables**:
```bash
# Master toggle
OAUTH2_ENABLED=false  # Set to true to enable

# Google
GOOGLE_OAUTH_ENABLED=false
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Microsoft
MICROSOFT_OAUTH_ENABLED=false
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT=common  # or specific tenant ID

# GitHub
GITHUB_OAUTH_ENABLED=false
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret

# Generic OIDC
OIDC_ENABLED=false
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_WELL_KNOWN_URL=https://provider.com/.well-known/openid-configuration
OIDC_PROVIDER_NAME=CustomOIDC  # Display name
```

**Security Features**:
- HttpOnly cookies prevent XSS attacks
- CSRF protection via FastAPI-Users
- State parameter prevents authorization code interception
- Last auth method protection prevents account lockout
- Environment validation at startup

**Why**: Reduces friction for user onboarding, supports multiple authentication methods, enables single sign-on across platforms.

#### Error Handling & Recovery
The application implements **production-grade error handling** with graceful recovery strategies:

**Custom Exception Hierarchy**:
All application errors inherit from `BlacklightException` with consistent structure:
- `NotFoundError` (404) - Resource not found
- `ValidationError` (422) - Input validation failures
- `PermissionDeniedError` (403) - Authorization failures
- `DatabaseError` (503) - DB connection/query failures (transient, retryable)
- `ExternalServiceError` (503) - LLM API failures (transient, retryable)
- `CircuitBreakerOpenError` (503) - Service temporarily unavailable
- `ConfigurationError` (500) - Fatal config errors (app crashes, requires fix)

**Specialized Exceptions**:
- `AgentNotFoundError`, `UserNotFoundError`, `RoleNotFoundError` - Domain-specific not found errors
- `LLMError` - LLM API-specific errors with provider context

**Error Response Format**:
All API errors return consistent JSON:
```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent abc123 not found",
    "details": {"agent_id": "abc123"},  // Only in development
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Retry Logic**:
Automatic retry with exponential backoff for transient failures:
```python
from src.blacklight.common.retry import retry_on_db_error, retry_on_llm_error

@retry_on_db_error(max_attempts=5)
async def query_database():
    # Database query that may fail transiently
    ...

@retry_on_llm_error(max_attempts=3)
async def call_llm_api():
    # LLM API call with retry
    ...
```

**Circuit Breaker**:
Prevents cascading failures when LLM API is down:
- Opens circuit after 5 consecutive failures (configurable)
- Blocks requests for 60 seconds (recovery timeout)
- Automatically tests recovery (half-open state)
- Used automatically for all LLM calls

**Global Exception Handlers**:
All exceptions are caught and formatted consistently:
- `BlacklightException` → Custom error response
- `HTTPException` → FastAPI-compatible error
- `RequestValidationError` → Pydantic validation errors
- `SQLAlchemyError` → Database error response
- `Exception` (catch-all) → Generic 500 error

**Error Settings** (`.env`):
```bash
# Auto-enabled in development, disabled in production
EXPOSE_ERROR_DETAILS=false

# Maximum retry attempts for transient failures
RETRY_MAX_ATTEMPTS=3

# Failures before opening circuit breaker
CIRCUIT_BREAKER_THRESHOLD=5
```

**Key Files**:
- `backend/src/blacklight/common/exceptions.py` - Custom exception hierarchy
- `backend/src/blacklight/common/error_schemas.py` - Error response models
- `backend/src/blacklight/middleware/error_handlers.py` - Global exception handlers
- `backend/src/blacklight/middleware/error_middleware.py` - Error handling middleware
- `backend/src/blacklight/common/retry.py` - Retry decorators
- `backend/src/blacklight/common/circuit_breaker.py` - Circuit breaker implementation

**Best Practices**:
- ✅ Use specific exceptions (`AgentNotFoundError`) instead of generic `HTTPException`
- ✅ Let global handlers format error responses (don't catch and re-raise)
- ✅ Use retry decorators for transient failures
- ✅ Don't catch `ConfigurationError` - let app crash for required fixes
- ✅ Include context in exception details (agent_id, user_id, etc.)

**Why**: Graceful recovery from transient failures, consistent error responses, prevents cascading failures, better debugging with request IDs and structured logging.

### Database Schema
- **users** - User accounts (id, email, hashed_password, role_id, is_active, is_superuser, is_verified)
- **user_settings** - User preferences (theme, custom_prompts, preferences JSON)
- **roles** - User roles for RBAC (id, name, description, permissions relationship)
- **permissions** - Granular permissions (resource, action, description)
- **audit_logs** - Security event tracking (login, registration, permission changes)
- **agents** - Agent definitions (id, status, description, spec JSON, cost metrics, user_id)
- **conversations** - Chat sessions between user and AI for agent creation (user_id, agent_id)
- **messages** - Individual chat messages (role, content, timestamps)
- **executions** - Agent run history (future feature)

**Important**: Always use Alembic migrations for schema changes, never manual ALTER TABLE. All tables use **AsyncSession** with SQLAlchemy 2.0 patterns.

### LLM Configuration
Multi-provider support via `common/llm_config.py`:
- **OpenAI**: gpt-4o-mini, gpt-4o
- **xAI Grok**: grok-4-fast-non-reasoning, grok-3
- **Local LMStudio**: Can be configured at `http://localhost:1234/v1`

Switch providers via environment variables:
```bash
LLM_PROVIDER=xai_grok              # or openai
LLM_MODEL=grok-4-fast-non-reasoning
GROK_API_KEY=your_key
```

For local inference with LMStudio, configure as OpenAI-compatible endpoint:
```bash
LLM_PROVIDER=openai
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=not-needed  # LMStudio doesn't require key
```

**Why abstracted**: Avoid vendor lock-in, easy A/B testing, cost optimization, local development.

## Environment Setup

### Backend `.env` (required)
```bash
# LLM Provider Configuration
LLM_PROVIDER=xai_grok                    # or openai, or custom for LMStudio
LLM_MODEL=grok-4-fast-non-reasoning

# API Keys
OPENAI_API_KEY=sk-...
GROK_API_KEY=xai-...

# Database (for Docker Compose - recommended)
DATABASE_URL=postgresql://agent_builder:agent_builder_dev@localhost:5432/agent_builder
# For local PostgreSQL without Docker:
# DATABASE_URL=postgresql://localhost/agent_builder

# Authentication (FastAPI-Users)
JWT_SECRET=your-secret-key-here-generate-with-openssl-rand-hex-32
# Generate with: openssl rand -hex 32

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend `.env` (optional)
```bash
VITE_API_URL=http://localhost:8000
```

## Important File Locations

### Backend Entry Points
- `backend/src/blacklight/main.py` - FastAPI app initialization, CORS, lifespan
- `backend/src/blacklight/features/agents/routes.py` - Agent API endpoints (chat, execute)
- `backend/src/blacklight/features/auth/routes.py` - Auth & settings endpoints
- `backend/src/blacklight/common/llm_config.py` - Multi-provider LLM setup
- `backend/src/blacklight/common/database.py` - Database session management

### Frontend Entry Points
- `frontend/app/root.tsx` - App layout with sidebar navigation, ThemeProvider
- `frontend/app/routes/create-agent.tsx` - Main chat interface for agent creation
- `frontend/app/routes/login.tsx` - Login page with shadcn/ui form
- `frontend/app/routes/signup.tsx` - User registration page
- `frontend/app/routes/settings.tsx` - User settings and theme preferences
- `frontend/app/lib/api.ts` - API client with SSE streaming support
- `frontend/app/lib/auth-api.ts` - Authentication API client (login, register, logout)
- `frontend/app/lib/settings-api.ts` - Settings API client (theme, custom prompts)

### Database
- `backend/alembic/versions/` - Migration files (numbered sequentially)
- `backend/src/blacklight/features/*/models.py` - SQLAlchemy ORM models (per feature)
- `backend/src/blacklight/features/*/repositories.py` - Data access layer (per feature)
- `backend/src/blacklight/common/base_repository.py` - Base model and repository classes

## Common Development Patterns

### Adding a New API Endpoint
1. Add route handler in the appropriate feature's `routes.py` (e.g., `features/agents/routes.py`)
2. Use dependency injection for database and services:
   ```python
   from src.blacklight.features.agents.dependencies import get_agent_builder_service

   @router.get("/agents/{agent_id}")
   async def get_agent(
       agent_id: str,
       service: AgentBuilderService = Depends(get_agent_builder_service)
   ):
       return await service.get_agent(agent_id)
   ```
3. Business logic goes in service classes (e.g., `features/agents/services.py`), not route handlers
4. Update frontend `app/lib/api.ts` to call new endpoint

### Adding a New Database Table
1. Ensure database is running: `docker compose up -d postgres`
2. Create ORM model in the feature's `models.py` (e.g., `features/agents/models.py`)
3. Create repository methods in the feature's `repositories.py`
4. Import the model in `alembic/env.py` for autogeneration
5. Generate migration: `uv run alembic revision --autogenerate -m "add table_name"`
6. Review migration in `alembic/versions/`, edit if needed
7. Apply: `uv run alembic upgrade head`

### Adding shadcn/ui Components
```bash
cd frontend
npx shadcn@latest add <component-name>
```
Components go in `frontend/app/components/ui/`.

### Adding Python Dependencies
```bash
cd backend
uv add <package-name>           # Production dependency
uv add --dev <package-name>     # Development dependency
```

### Streaming a New LLM Interaction
1. Create `StreamingCallbackHandler` instance
2. Get streaming LLM: `LLMConfig.get_llm(streaming=True, callbacks=[callback])`
3. Invoke LLM in background task
4. Yield from `callback.aiter()` in route handler
5. Return `EventSourceResponse` with generator function

## Testing Strategy

Tests are **colocated with the code they test** in `features/*/tests/` directories:

### Backend Tests
- **Location**: `backend/src/blacklight/features/*/tests/`
- **Unit Tests** (`test_repositories.py`, `test_services.py`) - Test in isolation with mocked dependencies
- **Integration Tests** (`test_repositories_integration.py`, `test_api_endpoints.py`) - Test with real database
- **System Tests** (`test_agent_flow.py`) - Test full end-to-end flows

**Running tests**:
```bash
cd backend
uv run pytest                    # Run all tests
uv run pytest -v                 # Verbose output
uv run pytest features/agents/   # Run tests for specific feature
uv run pytest --cov=src          # With coverage
```

### Frontend Tests
- Unit: Vitest for components and utilities
- E2E: Playwright for full user flows

## Troubleshooting

### Port 8000 in Use
```bash
lsof -ti:8000 | xargs kill -9
```

### Database Connection Errors
- Ensure PostgreSQL container is running: `docker compose ps`
- Start PostgreSQL if not running: `docker compose up -d postgres`
- Verify `DATABASE_URL` in `.env` matches Docker credentials
- Check database health: `docker compose exec postgres pg_isready -U agent_builder`
- View database logs: `docker compose logs postgres`

### Missing API Keys
Backend won't start without required API key for selected LLM_PROVIDER. Check `.env` has:
- `OPENAI_API_KEY` if `LLM_PROVIDER=openai`
- `GROK_API_KEY` if `LLM_PROVIDER=xai_grok`

### CORS Errors
Ensure `CORS_ORIGINS` in backend `.env` includes frontend URL (default: `http://localhost:5173`).

### Streaming Not Working
- Check browser console for EventSource errors
- Verify backend endpoint returns `EventSourceResponse`
- Ensure `streaming=True` when creating LLM

### uv Command Not Found
Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Prometheus Metrics & Observability

The application includes **comprehensive Prometheus metrics** for monitoring application performance, business events, and infrastructure health.

### Overview

Metrics are automatically collected for:
- **HTTP Requests**: Request count, latency, size by endpoint/method/status
- **Database**: Query duration, slow queries, connection pool stats
- **Business Events**: User activity, agent operations, executions
- **Circuit Breaker**: State transitions, failures, successes
- **System**: Python GC, process metrics

### Metrics Endpoint

Access metrics at: `http://localhost:8000/metrics`

```bash
# View all metrics
curl http://localhost:8000/metrics

# Query specific metrics (with grep)
curl -s http://localhost:8000/metrics | grep blacklight_http
```

### Available Metrics

#### HTTP Metrics (Automatic via prometheus-fastapi-instrumentator)
- `blacklight_http_requests_total` - Total HTTP requests (method, endpoint, status)
- `blacklight_http_request_duration_seconds` - Request latency histogram
- `blacklight_http_request_size_bytes` - Request body size
- `blacklight_http_response_size_bytes` - Response body size
- `blacklight_http_requests_in_progress` - Active requests gauge

#### Database Metrics
- `blacklight_db_query_duration_seconds` - Query execution time (by query type)
- `blacklight_db_slow_queries_total` - Count of slow queries (>1s by default)
- `blacklight_db_pool_size` - Connection pool size
- `blacklight_db_pool_checked_out` - Active connections
- `blacklight_db_pool_overflow` - Overflow connections
- `blacklight_db_errors_total` - Database errors (by error type)

#### Business Metrics
- `blacklight_users_registered_total` - User registrations (by method: email/oauth)
- `blacklight_user_logins_total` - Login attempts (method, status)
- `blacklight_user_logouts_total` - User logouts
- `blacklight_password_resets_total` - Password resets (status)
- `blacklight_permissions_denied_total` - Permission denials (resource, action)
- `blacklight_agents_created_total` - Agents created
- `blacklight_agents_updated_total` - Agent updates
- `blacklight_agents_deleted_total` - Agents deleted
- `blacklight_agent_builds_total` - Agent builds (status)
- `blacklight_agent_build_duration_seconds` - Build duration histogram
- `blacklight_agent_executions_total` - Executions (status)
- `blacklight_agent_execution_duration_seconds` - Execution duration histogram
- `blacklight_conversations_started_total` - Conversations started
- `blacklight_messages_sent_total` - Messages sent (by role: user/assistant)

#### Circuit Breaker Metrics
- `blacklight_circuit_breaker_state` - Circuit state (0=closed, 1=half-open, 2=open)
- `blacklight_circuit_breaker_failures_total` - Total failures
- `blacklight_circuit_breaker_successes_total` - Total successes
- `blacklight_circuit_breaker_opened_total` - Times circuit opened
- `blacklight_circuit_breaker_closed_total` - Times circuit closed

### Configuration

Configure Prometheus in `backend/.env`:

```bash
# Enable/disable Prometheus metrics export
PROMETHEUS_ENABLED=true

# Multiprocess mode for production (Gunicorn with multiple workers)
PROMETHEUS_MULTIPROCESS_MODE=false
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# Include exemplars (request IDs) in metrics
PROMETHEUS_INCLUDE_EXEMPLARS=true
```

### Custom Metrics

Add custom metrics using decorators or direct instrumentation:

```python
from src.blacklight.common.metrics import (
    track_duration,
    track_counter,
    track_errors,
    create_histogram,
    create_counter,
)

# Track function duration
@track_duration("custom_operation_duration_seconds", labels={"operation": "data_processing"})
async def process_data():
    # Your code here
    ...

# Count function calls
@track_counter("custom_events_total", labels={"event_type": "custom"})
async def handle_event():
    # Your code here
    ...

# Track errors
@track_errors("custom_errors_total", labels={"service": "external_api"})
async def call_external_api():
    # May raise exceptions
    ...

# Manual instrumentation
requests_counter = create_counter(
    "custom_requests_total",
    "Total custom requests",
    ["endpoint"]
)
requests_counter.labels(endpoint="/api/custom").inc()

duration_histogram = create_histogram(
    "custom_duration_seconds",
    "Custom operation duration",
    ["operation"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0)
)
duration_histogram.labels(operation="process").observe(2.5)
```

### Multiprocess Mode (Production with Gunicorn)

For production deployments with multiple workers, enable multiprocess mode:

**1. Update `.env`:**
```bash
PROMETHEUS_MULTIPROCESS_MODE=true
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
```

**2. Create Gunicorn configuration (`gunicorn_conf.py`):**
```python
# Number of worker processes
workers = 4

# Worker class (use uvicorn for async support)
worker_class = "uvicorn.workers.UvicornWorker"

# Prometheus multiprocess support
def on_starting(server):
    """Called just before the master process is initialized."""
    from src.blacklight.common.metrics.multiprocess import setup_multiprocess_mode
    setup_multiprocess_mode()

def child_exit(server, worker):
    """Called just after a worker has been exited."""
    from src.blacklight.common.metrics.multiprocess import mark_process_dead
    mark_process_dead()
```

**3. Run with Gunicorn:**
```bash
cd backend
uv run gunicorn -c gunicorn_conf.py src.blacklight.main:app
```

### Integration with Prometheus Server

**1. Install Prometheus** (macOS example):
```bash
brew install prometheus

# Or with Docker
docker run -p 9090:9090 -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

**2. Configure Prometheus (`prometheus.yml`):**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'blacklight'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**3. Access Prometheus UI:**
```
http://localhost:9090
```

### Example Queries

Query metrics in Prometheus UI or via API:

```promql
# Request rate (per second)
rate(blacklight_http_requests_total[5m])

# 95th percentile request latency
histogram_quantile(0.95, rate(blacklight_http_request_duration_seconds_bucket[5m]))

# Database connection pool usage
blacklight_db_pool_checked_out / blacklight_db_pool_size

# Agent creation rate (per minute)
rate(blacklight_agents_created_total[1m]) * 60

# User login success rate
rate(blacklight_user_logins_total{status="success"}[5m]) /
rate(blacklight_user_logins_total[5m])

# Circuit breaker open alerts
blacklight_circuit_breaker_state == 2
```

### Grafana Dashboards

Visualize metrics with Grafana:

**1. Install Grafana:**
```bash
brew install grafana

# Or with Docker
docker run -d -p 3000:3000 grafana/grafana
```

**2. Configure Prometheus data source:**
- URL: `http://localhost:9090`
- Access: Server (default)

**3. Import pre-built dashboards:**
- FastAPI overview (community dashboard ID: 16110)
- Python application monitoring (dashboard ID: 6417)

**4. Create custom dashboards** with panels for:
- Request rate and latency by endpoint
- Database query performance
- Business metrics (users, agents, executions)
- Circuit breaker state timeline
- Error rates and types

### Best Practices

- **Low Cardinality Labels**: Keep labels to 3-5 per metric, avoid IDs/timestamps
- **Meaningful Names**: Use `_total` suffix for counters, `_seconds` for durations
- **Buckets**: Choose histogram buckets appropriate for your use case
- **Alerting**: Set up Prometheus alerts for critical metrics (circuit breakers, error rates)
- **Retention**: Configure Prometheus retention policy for your storage needs
- **Security**: Protect `/metrics` endpoint in production (IP allowlist, authentication)

### Key Files

- `backend/src/blacklight/common/metrics/` - Metrics module
  - `registry.py` - Central registry and metric factories
  - `http_metrics.py` - HTTP instrumentation
  - `database_metrics.py` - Database metrics
  - `business_metrics.py` - Business event metrics
  - `decorators.py` - Custom metric decorators
  - `multiprocess.py` - Multiprocess mode support
- `backend/src/blacklight/common/db_logging.py` - Database metrics integration
- `backend/src/blacklight/common/business_events.py` - Business metrics integration
- `backend/src/blacklight/common/circuit_breaker.py` - Circuit breaker metrics
- `backend/src/blacklight/main.py` - Metrics setup

**Why**: Production-grade observability for monitoring, alerting, capacity planning, and debugging.

## Production Considerations

**Implemented**:
- ✅ **Authentication**: FastAPI-Users with cookie-based sessions, RBAC, audit logging
- ✅ **User Settings**: Persistent theme preferences and custom prompts
- ✅ **Async Database**: SQLAlchemy 2.0 with AsyncSession for better performance
- ✅ **CORS**: Configured for frontend origins
- ✅ **Database Migrations**: Alembic for schema version control
- ✅ **Code Quality**: Black and Ruff for backend, Prettier for frontend
- ✅ **CI/CD**: GitHub Actions for automated testing and staging deployment
- ✅ **Prometheus Metrics**: Comprehensive metrics for HTTP, database, business events, circuit breakers
- ✅ **Error Handling**: Retry logic, circuit breakers for LLM calls, graceful degradation
- ✅ **Structured Logging**: JSON logs with correlation IDs, component-level log levels, sensitive data sanitization
- ✅ **Health Checks**: `/health` endpoint for orchestration
- ✅ **Rate Limiting**: Per-IP rate limiting with slowapi

**Still Needed for Production**:
1. **Enhanced Monitoring**: Add Sentry/Datadog integration for error tracking and APM
2. **Production Secrets Management**: Use environment-specific secrets (AWS Secrets Manager, HashiCorp Vault)
3. **HTTPS/TLS**: Configure SSL certificates for production domains
4. **Database Backups**: Automated PostgreSQL backups and point-in-time recovery
5. **Load Testing**: Validate performance under realistic traffic
6. **CDN Integration**: Serve static frontend assets via CDN
7. **Prometheus Alerting**: Configure AlertManager for critical metric thresholds
8. **Grafana Dashboards**: Create custom dashboards for monitoring
9. **Security Hardening**: Implement CSP headers, rate limiting per user, DDoS protection
10. **Disaster Recovery**: Document and test backup/restore procedures

## Code Style

### TypeScript
- Use TypeScript strict mode
- Follow React Router v7 conventions
- Prefer function components with hooks
- Use shadcn/ui patterns for components

### Python
- Follow PEP 8
- Use type hints for all function signatures
- Docstrings for public APIs (Google style)
- Async/await for I/O operations

### Code Formatting

**Backend (Python)**:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting and import sorting
- Configuration in `pyproject.toml`

```bash
# Format backend code
cd backend
uv run black src/ tests/
uv run ruff check --fix src/ tests/
```

**Frontend (TypeScript/React)**:
- **Prettier** for code formatting
- Configuration in `.prettierrc`

```bash
# Format frontend code
cd frontend
npm run format
npm run format:check
```

**CI Enforcement**:
Both formatters run automatically in GitHub Actions CI pipeline. PRs failing format checks will be blocked from merging.

## Key Dependencies

### Backend Critical
- `langchain-core`, `langchain-openai` - LLM interactions
- `langgraph` - Agent workflow graphs
- `fastapi` - Web framework
- `sqlalchemy` - ORM (async with SQLAlchemy 2.0)
- `alembic` - Database migrations
- `sse-starlette` - SSE streaming
- `fastapi-users[sqlalchemy]` - Authentication with cookie-based sessions
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - JWT token handling
- `uv` - Fast Python package manager (replaces pip/poetry)

### Frontend Critical
- `react-router` - Routing and SSR
- `react-markdown` - Markdown rendering with code highlighting
- `@radix-ui/*` - Accessible UI primitives (via shadcn/ui)
- `tailwindcss` - Styling
- `sonner` - Toast notifications for user feedback

## MCP Servers Available

This repository has access to the following MCP servers:
- **context7** - Fetch up-to-date documentation for any library
- **playwright** - Browser automation for testing and web scraping
