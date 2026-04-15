from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.blacklight.common.logging import configure_logging
from src.blacklight.common.settings import settings
from src.blacklight.common.database import SessionLocal, engine
from src.blacklight.common.db_logging import setup_query_logging

from src.blacklight.features.auth.routes import router as auth_router
from src.blacklight.features.auth.admin_routes import admin_router
from src.blacklight.features.auth.services import PermissionService
from src.blacklight.features.agents.routes import router as agents_router
from sqlalchemy import text

# Initialize logging before anything else
configure_logging()

# Get logger for main module
logger = structlog.get_logger("blacklight.main")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Import OpenTelemetry (after logging is configured)
if settings.otel_enabled:
    from src.blacklight.common.otel import setup_otel, shutdown_otel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Tests database connection and initializes default roles and permissions on startup.
    """
    # Startup: Test database connection
    logger.info("application_starting", version="0.1.0")
    logger.info("testing_database_connection")

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_successful")

        # Set up query performance logging
        setup_query_logging(engine)
        logger.info("query_performance_logging_enabled", threshold_ms=settings.slow_query_threshold_ms)
    except Exception as e:
        logger.error(
            "database_connection_failed",
            error=str(e),
            exc_info=True
        )
        raise  # Fail fast if database is not available

    # Initialize default roles and permissions
    logger.info("initializing_default_roles_and_permissions")

    async with SessionLocal() as session:
        try:
            permission_service = PermissionService(session)
            await permission_service.initialize_default_roles_and_permissions()
            await session.commit()  # Commit initialization changes
            logger.info("default_roles_and_permissions_initialized")
        except Exception as e:
            logger.error(
                "failed_to_initialize_roles_and_permissions",
                error=str(e),
                exc_info=True
            )
            raise  # Fail fast if initialization fails

    logger.info("application_ready")
    yield

    # Shutdown: Clean up resources
    logger.info("application_shutdown")

    # Shut down OpenTelemetry (flush pending telemetry)
    if settings.otel_enabled:
        shutdown_otel()

    await engine.dispose()  # Dispose of connection pool


app = FastAPI(
    title="Blacklight API",
    description="Blacklight - AI Agent Builder Platform for creating and executing AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up OpenTelemetry (before middleware, after app creation)
if settings.otel_enabled:
    logger.info("setting_up_opentelemetry")
    setup_otel(app, engine)
    logger.info("opentelemetry_setup_complete")

# Register global exception handlers (must be done early)
from src.blacklight.middleware import register_exception_handlers
register_exception_handlers(app)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware (in reverse order - last added is executed first)
from src.blacklight.middleware import (
    AuditContextMiddleware,
    CorrelationIdMiddleware,
    LoggingMiddleware,
)

# Add Correlation ID middleware (must be added early to generate request IDs)
app.add_middleware(CorrelationIdMiddleware)

# Add Request Logging middleware (logs all requests with correlation IDs)
app.add_middleware(LoggingMiddleware)

# Add Audit Context Middleware (for ContextVars support in decorators)
app.add_middleware(AuditContextMiddleware)

# Optional: Add CSRF middleware (uncomment to enable)
# from src.blacklight.middleware import CSRFMiddleware
# app.add_middleware(
#     CSRFMiddleware,
#     cookie_secure=settings.is_production
# )

# Include routers
app.include_router(auth_router, prefix="/api", tags=["auth"])  # Auth routes include /auth and /settings
app.include_router(admin_router, prefix="/api", tags=["admin"])  # Admin routes for user/role management
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])


@app.get("/")
async def root():
    return {"message": "Blacklight API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
