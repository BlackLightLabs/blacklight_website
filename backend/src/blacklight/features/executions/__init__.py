"""
Executions feature module

Provides agent execution functionality including models, repositories,
services, schemas, and dependencies for running created agents.

NOTE: This __init__.py does NOT import dependencies to avoid circular imports.
The agents.models module imports Execution directly from .models, which would
trigger this __init__.py. If we imported from dependencies here, it would create:
agents.models → executions.__init__ → executions.dependencies → agents.repositories → agents.models (circular!)

Dependencies should be imported directly where needed, not through this __init__.py.
"""

# Only import models - NO dependencies, repositories, or services to avoid circular imports
from src.blacklight.features.executions.models import Execution, ExecutionStatusEnum

__all__ = [
    # Models only - other exports removed to prevent circular imports
    "Execution",
    "ExecutionStatusEnum",
]
