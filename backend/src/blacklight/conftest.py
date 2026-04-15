"""
Pytest configuration and shared fixtures
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.blacklight.common.base_repository import Base
from src.blacklight.common.database import get_db
from src.blacklight.features.agents.models import Agent, AgentStatusEnum, Conversation, Message
from src.blacklight.features.agents.repositories import (
    AgentRepository,
    ConversationRepository,
)
from src.blacklight.features.auth.models import User, Role, Permission
from src.blacklight.features.auth.repositories import UserRepository, RoleRepository
from src.blacklight.features.auth.routes import current_active_user
from src.blacklight.features.executions.repositories import ExecutionRepository
from src.blacklight.main import app


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.refresh = Mock()
    session.add = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def test_user_id():
    """Provide a consistent test user ID for non-async tests"""
    return 1


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for integration tests"""
    # Add check_same_thread=False for SQLite thread safety with FastAPI TestClient
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_agent_data(test_user_id):
    """Sample agent data for tests"""
    return {
        "agent_id": "test-agent-123",
        "status": AgentStatusEnum.CREATING,
        "description": "Test agent",
        "spec": {"name": "test", "steps": []},
        "graph_data": None,
        "total_executions": 0,
        "total_cost": 0.0,
        "estimated_cost_per_run": 0.10,
        "user_id": test_user_id,
    }


@pytest.fixture
def sample_agent(sample_agent_data):
    """Create a sample Agent model instance"""
    # Agent model uses 'id' not 'agent_id'
    data = sample_agent_data.copy()
    data["id"] = data.pop("agent_id")
    return Agent(**data)


@pytest.fixture
def sample_conversation_data(sample_agent_data, test_user_id):
    """Sample conversation data for tests"""
    return {
        "id": "conv-123",
        "agent_id": sample_agent_data["agent_id"],
        "user_id": test_user_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_conversation(sample_conversation_data):
    """Create a sample Conversation model instance"""
    return Conversation(**sample_conversation_data)


@pytest.fixture
def sample_message_data(sample_conversation_data):
    """Sample message data for tests"""
    return {
        "id": "msg-123",
        "conversation_id": sample_conversation_data["id"],
        "role": "user",
        "content": "I want to create an agent",
        "timestamp": datetime.utcnow(),
    }


@pytest.fixture
def sample_message(sample_message_data):
    """Create a sample Message model instance"""
    return Message(**sample_message_data)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    mock_response = Mock()
    mock_response.content = "I can help you create an agent. What should it do?"
    return mock_response


@pytest.fixture
def mock_llm():
    """Mock LLM instance"""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def test_db(in_memory_db):
    """Alias for in_memory_db for compatibility"""
    return in_memory_db


@pytest.fixture
def agent_repo(in_memory_db):
    """Create an AgentRepository with test database"""
    return AgentRepository(in_memory_db)


@pytest.fixture
def conversation_repo(in_memory_db):
    """Create a ConversationRepository with test database"""
    return ConversationRepository(in_memory_db)


@pytest.fixture
def execution_repo(in_memory_db):
    """Create an ExecutionRepository with test database"""
    return ExecutionRepository(in_memory_db)


@pytest.fixture
def client(in_memory_db):
    """Create a FastAPI TestClient with test database"""

    # Override the get_db dependency to use test database
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


# Async fixtures for new async tests
@pytest_asyncio.fixture
async def async_db():
    """Create an in-memory async SQLite database for async integration tests"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(async_db):
    """Create a test user for tests that require authentication

    Creates a superuser for testing to bypass permission checks.
    """
    user_repo = UserRepository(async_db)
    role_repo = RoleRepository(async_db)

    # Create a default user role if it doesn't exist
    role = await role_repo.get_by_name("user")
    if not role:
        role = await role_repo.create(name="user", description="Default user role")

    # Create test user as superuser to bypass permission checks
    user = await user_repo.create(
        email="test@example.com",
        hashed_password="hashed_password_123",
        role_id=role.id,
        is_active=True,
        is_superuser=True,  # Superuser bypasses all permission checks
        is_verified=True,
    )

    return user


@pytest_asyncio.fixture
async def async_agent_repo(async_db):
    """Create an async AgentRepository with test database"""
    return AgentRepository(async_db)


@pytest_asyncio.fixture
async def async_conversation_repo(async_db):
    """Create an async ConversationRepository with test database"""
    return ConversationRepository(async_db)


@pytest_asyncio.fixture
async def async_execution_repo(async_db):
    """Create an async ExecutionRepository with test database"""
    return ExecutionRepository(async_db)


@pytest_asyncio.fixture
async def async_client(async_db, test_user):
    """Create an async HTTP client with test database and authenticated user"""

    # Override the get_db dependency
    async def override_get_db():
        yield async_db

    # Override the current_active_user dependency to return test user
    async def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_active_user] = override_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
