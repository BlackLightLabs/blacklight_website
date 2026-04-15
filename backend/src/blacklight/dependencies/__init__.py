"""
FastAPI Dependency Injection Providers

This module provides common dependencies that can be injected into route handlers.
Most feature-specific dependencies are now in their respective feature modules
(e.g., src.blacklight.features.agents.dependencies).

Available Dependencies:

Database:
    - get_db: Provides async database session (AsyncSession)

    Usage:
        ```python
        async def my_route(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
        ```

Authentication & Authorization:
    - RequirePermission: Dependency class for permission checks
    - RequireRole: Dependency class for role-based access
    - PermissionChecker: Base class for custom permission logic
    - check_resource_permission: Check permission for specific resource
    - require_superuser: Require superuser status

    Usage:
        ```python
        # Require specific permission
        @router.post("/agents")
        async def create_agent(
            user: User = Depends(RequirePermission("agents:create"))
        ):
            pass

        # Require role
        @router.get("/admin/users")
        async def list_users(
            user: User = Depends(RequireRole("admin"))
        ):
            pass

        # Require superuser
        @router.delete("/system/purge")
        async def purge_system(
            user: User = Depends(require_superuser)
        ):
            pass
        ```

Feature-Specific Dependencies:
    For feature-specific dependencies (repositories, services), import from
    the feature's dependencies module:

    ```python
    from src.blacklight.features.agents.dependencies import (
        get_agent_builder_service,
        get_agent_repository,
        get_conversation_repository,
    )

    from src.blacklight.features.auth.dependencies import (
        get_auth_service,
        get_user_repository,
        get_permission_service,
    )
    ```

Dependency Graph:
    ```
    Route Handler
        ↓
    Service (business logic)
        ↓
    Repository (data access)
        ↓
    Database Session (get_db)
    ```

Best Practices:
    1. Always use Depends() for dependency injection
    2. Never instantiate services/repositories directly in routes
    3. Use type hints for all dependencies
    4. Keep dependencies pure (no side effects in providers)
    5. Test dependencies by overriding them in test fixtures

For more information on the dependency injection pattern, see CLAUDE.md.
"""

from src.blacklight.dependencies.database import get_db
from src.blacklight.dependencies.permissions import (
    PermissionChecker,
    RequirePermission,
    RequireRole,
    check_resource_permission,
    require_superuser,
)

__all__ = [
    "get_db",
    "PermissionChecker",
    "RequirePermission",
    "RequireRole",
    "check_resource_permission",
    "require_superuser",
]
