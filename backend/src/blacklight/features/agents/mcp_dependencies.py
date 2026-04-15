"""
MCP Dependency Injection

FastAPI dependency providers for MCP services.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.dependencies.database import get_db
from src.blacklight.features.agents.mcp_service import MCPService


async def get_mcp_service(db: AsyncSession = get_db()) -> MCPService:
    """
    Get MCP service instance with database session.

    Args:
        db: Database session from dependency injection

    Returns:
        MCPService instance
    """
    return MCPService(db)
