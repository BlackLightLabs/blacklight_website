"""
Execution repository for managing execution records

Provides data access layer for execution CRUD operations and queries.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.common.base_repository import BaseRepository
from src.blacklight.features.executions.models import Execution, ExecutionStatusEnum


class ExecutionRepository(BaseRepository[Execution]):
    """
    Repository for Execution model operations.

    Manages agent execution records and their lifecycle.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with the Execution model"""
        super().__init__(Execution, db)

    async def create_execution(
        self, agent_id: str, input_data: dict | None = None, execution_id: str | None = None
    ) -> Execution:
        """
        Create a new execution record.

        Args:
            agent_id: ID of the agent being executed
            input_data: Input data for the execution
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            The created Execution instance
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())

        return await self.create(
            id=execution_id,
            agent_id=agent_id,
            status=ExecutionStatusEnum.PENDING,
            input_data=input_data or {},
        )

    async def update_status(
        self,
        execution_id: str,
        status: ExecutionStatusEnum,
        output_data: dict | None = None,
        error_message: str | None = None,
    ) -> Execution | None:
        """
        Update execution status and optionally set output/error.

        Args:
            execution_id: The execution ID
            status: New status
            output_data: Optional output data
            error_message: Optional error message

        Returns:
            Updated execution or None if not found
        """
        update_data: dict[str, Any] = {"status": status}

        if status == ExecutionStatusEnum.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()

        if output_data is not None:
            update_data["output_data"] = output_data

        if error_message is not None:
            update_data["error_message"] = error_message

        return await self.update(execution_id, **update_data)

    async def set_cost(self, execution_id: str, cost: float) -> Execution | None:
        """
        Set the cost for an execution.

        Args:
            execution_id: The execution ID
            cost: Execution cost

        Returns:
            Updated execution or None if not found
        """
        return await self.update(execution_id, cost=cost)

    async def get_by_agent_id(self, agent_id: str, limit: int = 100) -> list[Execution]:
        """
        Get all executions for a specific agent.

        Args:
            agent_id: The agent ID
            limit: Maximum number of executions to return

        Returns:
            List of executions ordered by start time (most recent first)
        """
        stmt = (
            select(Execution)
            .filter(Execution.agent_id == agent_id)
            .order_by(Execution.started_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_executions(self) -> list[Execution]:
        """
        Get all pending executions.

        Returns:
            List of pending executions
        """
        stmt = select(Execution).filter(Execution.status == ExecutionStatusEnum.PENDING)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_running_executions(self) -> list[Execution]:
        """
        Get all running executions.

        Returns:
            List of running executions
        """
        stmt = select(Execution).filter(Execution.status == ExecutionStatusEnum.RUNNING)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
