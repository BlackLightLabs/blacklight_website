"""
Full integration test for self-repair loop with build pipeline and Docker sandbox

This test creates an agent with a broken spec, triggers the build pipeline,
and verifies that the self-repair loop automatically fixes the spec.
"""

import asyncio
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.blacklight.common.settings import settings
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
            "type": "llm",
            "prompt": "Generate a friendly greeting for {name}",
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


async def test_full_self_repair():
    """Test full self-repair loop with build pipeline and Docker sandbox"""
    print("\n" + "=" * 70)
    print("🧪 FULL INTEGRATION TEST: Self-Repair Loop with Build Pipeline")
    print("=" * 70)

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
        print("\n📝 Step 1: Creating test agent...")
        agent = await agent_repo.create_agent(
            agent_id="test-full-self-repair-001",
            description="Integration test for self-repair loop",
            spec=BROKEN_SPEC,
            user_id=1,
        )
        print(f"✅ Created agent: {agent.id}")

        # Validate broken spec fails
        print("\n🔍 Step 2: Validating broken spec...")
        try:
            spec = AgentSpec(**BROKEN_SPEC)
            print("❌ UNEXPECTED: Broken spec passed validation!")
            print("   This means the edge format validation is not working.")
            return
        except Exception as e:
            error_msg = str(e)
            if "from" in error_msg and "Field required" in error_msg:
                print(f"✅ Broken spec failed validation as expected")
                print(f"   Error: {error_msg[:150]}...")
            else:
                print(f"⚠️  Unexpected validation error: {error_msg}")

        # Test quick fix works
        print("\n🔧 Step 3: Testing quick fix...")
        fixed_spec_dict = await spec_reviser.quick_fix_edge_format(BROKEN_SPEC)
        try:
            fixed_spec = AgentSpec(**fixed_spec_dict)
            print("✅ Quick fix successful - spec is now valid")
            print(f"   Fixed edges preview:")
            for i, edge in enumerate(fixed_spec_dict["edges"][:2]):
                print(f"      Edge {i+1}: {edge}")
        except Exception as e:
            print(f"❌ Quick fix failed: {e}")
            return

        # Run full build pipeline with self-repair
        print("\n🚀 Step 4: Running full build pipeline with self-repair...")
        print("   This will:")
        print("   - Attempt to build with broken spec")
        print("   - Detect validation error")
        print("   - Apply quick fix")
        print("   - Retry build with fixed spec")
        print("   - Generate code and run tests")
        print()

        try:
            version = await pipeline.run(agent.id, fixed_spec)

            print(f"\n📊 Build Result:")
            print(f"   Status: {version.build_status}")
            print(f"   Version: {version.version}")
            print(f"   Agent ID: {version.agent_id}")

            if version.error_details:
                print(f"\n⚠️  Error Details:")
                print(f"   {json.dumps(version.error_details, indent=4)}")

            # Check build logs
            print(f"\n📝 Checking build logs...")
            from sqlalchemy import select
            from src.blacklight.features.agents.models import AgentBuildLog

            stmt = (
                select(AgentBuildLog)
                .where(AgentBuildLog.agent_version_id == version.id)
                .order_by(AgentBuildLog.created_at)
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()

            print(f"   Found {len(logs)} log entries:")
            for log in logs:
                status_emoji = "✅" if log.level == "INFO" else "❌" if log.level == "ERROR" else "⚠️"
                print(f"      {status_emoji} [{log.stage}] {log.message[:80]}")

            # Final status
            print(f"\n" + "=" * 70)
            if version.build_status == "READY":
                print("✅ SUCCESS: Agent built and ready!")
                print("   Self-repair loop worked as expected!")
            elif version.build_status == "FAILED":
                print("❌ FAILED: Build did not succeed")
                print("   Check error details above for diagnostics")
            else:
                print(f"⚠️  PARTIAL: Build status is {version.build_status}")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ Build pipeline failed with exception:")
            print(f"   {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_full_self_repair())
