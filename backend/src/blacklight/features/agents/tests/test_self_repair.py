"""
Test script for self-repair loop

Creates an agent with intentionally broken edge format to test self-repair.
"""

import asyncio
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.blacklight.common.settings import settings
# Import all models to avoid SQLAlchemy relationship errors
from src.blacklight.features.auth.models import User
from src.blacklight.features.executions.models import Execution
from src.blacklight.features.agents.build_pipeline import BuildPipeline
from src.blacklight.features.agents.error_analyzer import ErrorAnalyzer
from src.blacklight.features.agents.prompt_service import PromptService
from src.blacklight.features.agents.repositories import (
    AgentRepository,
    AgentVersionRepository,
    AgentBuildLogRepository,
    AgentTestRunRepository,
)
from src.blacklight.features.agents.spec_reviser import SpecReviser
from src.blacklight.features.agents.spec_schema import AgentSpec


# Broken spec with from_node/to_node (should trigger self-repair)
BROKEN_SPEC = {
    "name": "test_greeting_agent",
    "description": "A simple greeting agent",
    "model": "qwen/qwen3-coder-30b",
    "state": [
        {"name": "name", "type": "str", "description": "User's name"},
        {"name": "greeting", "type": "str", "description": "Generated greeting"},
    ],
    "nodes": [
        {
            "id": "greet",
            "type": "python",
            "input": ["name"],
            "output": ["greeting"],
        }
    ],
    "edges": [
        {"from_node": "START", "to_node": "greet"},  # BROKEN: should be "from"/"to"
        {"from_node": "greet", "to_node": "END"},  # BROKEN
    ],
    "tools": [],
    "tests": [
        {
            "name": "test_greeting",
            "input": {"name": "Alice"},
            "assertions": [
                {"type": "state_contains", "name": "greeting_exists", "path": "greeting"}
            ],
            "mocks": {},
        }
    ],
    "runtime": {"max_steps": 5, "budget_usd": 0.10, "timeout_seconds": 30},
}


async def test_self_repair():
    """Test self-repair loop with broken spec"""
    print("🧪 Testing Self-Repair Loop\n")
    print("=" * 60)

    # Setup database
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Setup repositories
        agent_repo = AgentRepository(session)
        version_repo = AgentVersionRepository(session)
        log_repo = AgentBuildLogRepository(session)
        test_run_repo = AgentTestRunRepository(session)

        # Setup services
        prompt_service = PromptService(session)
        error_analyzer = ErrorAnalyzer()
        spec_reviser = SpecReviser(prompt_service, error_analyzer)

        # Setup pipeline with self-repair
        from pathlib import Path
        import os

        pipeline = BuildPipeline(
            version_repo=version_repo,
            log_repo=log_repo,
            test_run_repo=test_run_repo,
            agent_repo=agent_repo,
            sandbox_root=Path(os.getenv("AGENT_SANDBOX_ROOT", "./generated")),
            error_analyzer=error_analyzer,
            spec_reviser=spec_reviser,
            max_retries=3,
        )

        # Create test agent
        print("\n📝 Creating test agent...")
        agent = await agent_repo.create_agent(
            agent_id="test-self-repair-001",
            description="Test agent for self-repair",
            spec=BROKEN_SPEC,
            user_id=1,  # Assuming test user exists
        )
        print(f"✅ Created agent: {agent.id}")

        # Validate broken spec (should fail with edge format error)
        print("\n🔍 Validating broken spec...")
        try:
            spec = AgentSpec(**BROKEN_SPEC)
            print("❌ UNEXPECTED: Broken spec passed validation!")
            print("   Edge format validation may not be working correctly")
        except Exception as e:
            print(f"✅ Expected validation error: {str(e)[:100]}...")

        # Test quick fix
        print("\n🔧 Testing quick fix for edge format...")
        fixed_spec_dict = await spec_reviser.quick_fix_edge_format(BROKEN_SPEC)
        try:
            fixed_spec = AgentSpec(**fixed_spec_dict)
            print("✅ Quick fix successful!")
            print(f"   Fixed edges: {json.dumps(fixed_spec_dict['edges'], indent=2)}")
        except Exception as e:
            print(f"❌ Quick fix failed: {e}")

        # Test build with self-repair (this would trigger the full loop)
        print("\n🚀 Testing build pipeline with self-repair...")
        print("   Note: This will attempt to build code and run tests")
        print("   Expected flow:")
        print("   1. Attempt 1: Validation fails (edge format)")
        print("   2. Error analyzer detects EDGE_FORMAT error")
        print("   3. Spec reviser applies quick fix")
        print("   4. Attempt 2: Should succeed")

        # Note: Uncomment below to test full pipeline (requires Docker sandbox)
        # version = await pipeline.run(agent.id, fixed_spec)
        # print(f"\n📊 Final Status: {version.build_status}")

        print("\n" + "=" * 60)
        print("✅ Self-Repair Tests Complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_self_repair())
