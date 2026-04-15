"""
Base Repository class with common CRUD operations

This abstract base class provides generic database operations that can be
inherited by specific repository classes.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# SQLAlchemy declarative base for ORM models
class Base(DeclarativeBase):
    pass

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=Any)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.

    This class uses generics to provide type-safe CRUD operations for
    any SQLAlchemy model that inherits from Base.

    Attributes:
        model: The SQLAlchemy model class this repository manages
        db: The SQLAlchemy async database session
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize the repository with a model class and database session.

        Args:
            model: The SQLAlchemy model class
            db: The async database session
        """
        self.model = model
        self.db = db

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record in the database.

        Note: This method does NOT commit the transaction. The caller (service layer)
        is responsible for committing or rolling back the transaction. This allows
        for atomic multi-step operations.

        Args:
            **kwargs: Field values for the new record

        Returns:
            The created model instance (with ID assigned after flush)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()  # Flush to get ID, but don't commit
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, id: str) -> ModelType | None:
        """
        Retrieve a record by its ID.

        Args:
            id: The record ID

        Returns:
            The model instance if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        Retrieve all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: str, **kwargs) -> ModelType | None:
        """
        Update a record by its ID.

        Note: This method does NOT commit the transaction. The caller (service layer)
        is responsible for committing or rolling back the transaction.

        Args:
            id: The record ID
            **kwargs: Fields to update

        Returns:
            The updated model instance if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = await self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            await self.db.flush()  # Flush changes, but don't commit
            await self.db.refresh(instance)
        return instance

    async def delete(self, id: str) -> bool:
        """
        Delete a record by its ID.

        Note: This method does NOT commit the transaction. The caller (service layer)
        is responsible for committing or rolling back the transaction.

        Args:
            id: The record ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = await self.get_by_id(id)
        if instance:
            await self.db.delete(instance)
            await self.db.flush()  # Flush deletion, but don't commit
            return True
        return False

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists by its ID.

        Args:
            id: The record ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        count = result.scalar()
        return (count or 0) > 0

    async def count(self) -> int:
        """
        Count total records.

        Returns:
            Total number of records
        """
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
