"""
Audit Logging Utilities

Provides DRY patterns for audit logging:
1. AuditLog dependency - For route-level automatic logging
2. @audit_log decorator - For service method logging
3. Context management - Automatic request context extraction

Usage Examples:

    # Route-level logging (dependency injection):
    @router.post("/agents")
    async def create_agent(
        user: User = Depends(RequirePermission("agents:create")),
        _audit: None = Depends(AuditLog("agent_management", "agent_created"))
    ):
        ...

    # Service-level logging (decorator):
    @audit_log("role_management", "role_assigned")
    async def assign_role(self, user_id: int, role_name: str):
        ...

    # Manual logging with context:
    async with audit_context():
        await log_audit_event(db, "custom_event", "custom_action", user_id=user.id)
"""

from contextvars import ContextVar
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.database import get_db
from src.blacklight.features.auth.models import User
from src.blacklight.features.auth.repositories import AuditLogRepository

# Avoid circular import by using TYPE_CHECKING
if TYPE_CHECKING:
    from src.blacklight.features.auth.routes import current_active_user

# Context variables for request-scoped data
# These are set by the audit context middleware
_request_context: ContextVar[Optional[Request]] = ContextVar("_request_context", default=None)
_user_context: ContextVar[Optional[User]] = ContextVar("_user_context", default=None)
_db_context: ContextVar[Optional[AsyncSession]] = ContextVar("_db_context", default=None)


def get_request_context() -> Optional[Request]:
    """Get the current request from context"""
    return _request_context.get()


def get_user_context() -> Optional[User]:
    """Get the current user from context"""
    return _user_context.get()


def get_db_context() -> Optional[AsyncSession]:
    """Get the current database session from context"""
    return _db_context.get()


def set_request_context(request: Request):
    """Set the current request in context"""
    _request_context.set(request)


def set_user_context(user: Optional[User]):
    """Set the current user in context"""
    _user_context.set(user)


def set_db_context(db: AsyncSession):
    """Set the current database session in context"""
    _db_context.set(db)


def extract_request_context(request: Optional[Request] = None) -> dict[str, Any]:
    """
    Extract IP address and user agent from request

    Args:
        request: FastAPI Request object (uses context if not provided)

    Returns:
        Dictionary with ip_address and user_agent
    """
    if request is None:
        request = get_request_context()

    if request is None:
        return {"ip_address": None, "user_agent": None}

    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    event_action: str,
    user_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Log an audit event with automatic context extraction

    Args:
        db: Database session
        event_type: Type of event (e.g., 'login', 'agent_management')
        event_action: Specific action (e.g., 'login_success', 'agent_created')
        user_id: Optional user ID (uses context if not provided)
        details: Optional additional event details
        request: Optional request object (uses context if not provided)
    """
    audit_repo = AuditLogRepository(db)

    # Extract context
    context = extract_request_context(request)

    # Use context user if user_id not provided
    if user_id is None:
        user = get_user_context()
        user_id = user.id if user else None

    await audit_repo.log_event(
        event_type=event_type,
        event_action=event_action,
        user_id=user_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        details=details,
    )


def make_audit_logger(event_type: str, event_action: str, details: Optional[dict[str, Any]] = None):
    """
    Factory function to create an audit logging dependency

    This avoids circular imports by not importing current_active_user directly.

    Usage:
        from src.blacklight.features.auth.routes import current_active_user

        @router.post("/agents")
        async def create_agent(
            current_user: User = Depends(current_active_user),
            db: AsyncSession = Depends(get_db),
            _audit: None = Depends(make_audit_logger("agent_management", "agent_created"))
        ):
            # Audit is logged automatically using user from context
            ...
    """
    async def audit_dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ):
        # Get user from context (set by middleware or route)
        user = get_user_context()

        # Set context for downstream usage
        set_request_context(request)
        set_db_context(db)

        # Log the event
        await log_audit_event(
            db=db,
            event_type=event_type,
            event_action=event_action,
            user_id=user.id if user else None,
            details=details,
            request=request,
        )

    return audit_dependency


class AuditLog:
    """
    FastAPI dependency class for automatic route-level audit logging

    DEPRECATED: Use make_audit_logger() function instead to avoid circular imports.

    Logs the event when the route completes successfully.
    For failed requests, use error handling middleware.

    Usage (with explicit user dependency):
        from src.blacklight.features.auth.routes import current_active_user

        @router.post("/agents")
        async def create_agent(
            current_user: User = Depends(current_active_user),
            db: AsyncSession = Depends(get_db),
        ):
            # Set user context first
            from src.blacklight.common.audit import set_user_context
            set_user_context(current_user)

            # Then use audit logging
            await log_audit_event(db, "agent_management", "agent_created")
            ...
    """

    def __init__(
        self,
        event_type: str,
        event_action: str,
        details: Optional[dict[str, Any]] = None,
        details_fn: Optional[Callable[[], dict[str, Any]]] = None,
    ):
        """
        Initialize audit log dependency

        Args:
            event_type: Type of event (e.g., 'agent_management', 'role_management')
            event_action: Specific action (e.g., 'agent_created', 'role_assigned')
            details: Static details to log
            details_fn: Function to generate details dynamically
        """
        self.event_type = event_type
        self.event_action = event_action
        self.details = details
        self.details_fn = details_fn

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        """
        Log audit event with automatic context extraction

        Gets user from context (set by middleware or route dependency).

        Args:
            request: FastAPI request
            db: Database session
        """
        # Get user from context
        user = get_user_context()

        # Set context for downstream usage
        set_request_context(request)
        set_db_context(db)

        # Prepare details
        details = self.details or {}
        if self.details_fn:
            details.update(self.details_fn())

        # Log the event
        await log_audit_event(
            db=db,
            event_type=self.event_type,
            event_action=self.event_action,
            user_id=user.id if user else None,
            details=details if details else None,
            request=request,
        )


def audit_log(
    event_type: str,
    event_action: str,
    include_args: bool = False,
    user_id_param: Optional[str] = None,
):
    """
    Decorator for service method audit logging

    Automatically logs when the decorated method completes successfully.
    Uses ContextVars for request context (requires middleware setup).

    Usage:
        @audit_log("role_management", "role_assigned")
        async def assign_role(self, user_id: int, role_name: str):
            ...

        @audit_log("agent_management", "agent_created", include_args=True)
        async def create_agent(self, spec: dict):
            ...

        @audit_log("user_management", "user_deleted", user_id_param="target_user_id")
        async def delete_user(self, target_user_id: int):
            ...

    Args:
        event_type: Type of event (e.g., 'role_management')
        event_action: Specific action (e.g., 'role_assigned')
        include_args: Include function arguments in audit details
        user_id_param: Name of the parameter containing the target user_id
                      (defaults to current user from context)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first
            result = await func(*args, **kwargs)

            # Get database session from context
            db = get_db_context()
            if db is None:
                # If no context, try to get from self (for service methods)
                if args and hasattr(args[0], "db"):
                    db = args[0].db
                else:
                    # Cannot log without database session
                    return result

            # Prepare details
            details = {}
            if include_args:
                # Capture function arguments (excluding self)
                import inspect

                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Skip 'self' and 'db' parameters
                details = {
                    k: v
                    for k, v in bound_args.arguments.items()
                    if k not in ("self", "db", "cls")
                }

            # Determine user_id for the audit log
            user_id = None
            if user_id_param and user_id_param in kwargs:
                user_id = kwargs[user_id_param]
            elif user_id_param and args:
                # Try to find in args by parameter name
                import inspect

                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                if user_id_param in param_names:
                    param_index = param_names.index(user_id_param)
                    if param_index < len(args):
                        user_id = args[param_index]

            # Log the event
            await log_audit_event(
                db=db,
                event_type=event_type,
                event_action=event_action,
                user_id=user_id,
                details=details if details else None,
            )

            return result

        return wrapper

    return decorator


class AuditContext:
    """
    Context manager for setting audit context

    Usage:
        async with AuditContext(request, user, db):
            # All audit_log decorators within this context will use these values
            await some_service_method()
    """

    def __init__(
        self, request: Optional[Request] = None, user: Optional[User] = None, db: Optional[AsyncSession] = None
    ):
        self.request = request
        self.user = user
        self.db = db
        self.tokens = []

    async def __aenter__(self):
        """Set context on enter"""
        if self.request:
            self.tokens.append(_request_context.set(self.request))
        if self.user:
            self.tokens.append(_user_context.set(self.user))
        if self.db:
            self.tokens.append(_db_context.set(self.db))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Reset context on exit"""
        for token in self.tokens:
            token.var.reset(token)
