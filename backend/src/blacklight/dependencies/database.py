"""
Database dependency for FastAPI dependency injection

This module provides the database session dependency that can be injected
into route handlers and other dependencies.
"""

from src.blacklight.common.database import get_db

__all__ = ["get_db"]
