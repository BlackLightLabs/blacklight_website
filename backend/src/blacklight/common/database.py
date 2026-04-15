"""
Database session management for SQLAlchemy

This module provides database connection and session management using
SQLAlchemy. It creates the engine, session factory, and dependency function
for FastAPI's dependency injection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.blacklight.common.settings import settings

# Get database URL from settings and convert to async URL
DATABASE_URL = settings.database_url

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is required")

# Convert postgresql:// to postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async SQLAlchemy engine with configuration from settings
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=settings.database_pool_pre_ping,  # Verify connections before using them
    pool_size=settings.database_pool_size,  # Connection pool size
    max_overflow=settings.database_max_overflow,  # Max connections beyond pool_size
    echo=settings.database_echo,  # Set to True for SQL query logging during development
)

# Create SessionLocal class for database sessions
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage in route handlers:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass

    Yields:
        AsyncSession: SQLAlchemy async database session

    The session is automatically committed on successful completion,
    and rolled back if an exception occurs.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()  # Explicit commit on success
        except Exception:
            await session.rollback()  # Explicit rollback on error
            raise
