#!/usr/bin/env python3
"""
Check agent build status with test report details.

This script is particularly useful for viewing test reports and
understanding why agents failed their build verification tests.

Usage:
    python check_new_agent.py <agent_id> [--limit N]
    python check_new_agent.py --help

Example:
    python check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1
    python check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1 --limit 5
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.blacklight.common.settings import settings


async def check_new_agent(agent_id: str, limit: int = 3) -> None:
    """
    Check agent build status with detailed test reports.

    Args:
        agent_id: UUID of the agent to check
        limit: Maximum number of versions to display (default: 3)

    Displays:
        - Agent basic info
        - Recent versions with test reports
        - Failed test details and assertions
    """
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            # Get the agent
            agent_result = await session.execute(
                text("""
                    SELECT id, status, description, created_at, updated_at
                    FROM agents
                    WHERE id = :agent_id
                """),
                {"agent_id": agent_id}
            )

            agent = agent_result.first()

            if not agent:
                print(f"❌ Agent not found: {agent_id}")
                return

            print(f"✓ Agent found: {agent_id}")
            print(f"  Status: {agent.status}")
            print(f"  Description: {agent.description}")
            print(f"  Created: {agent.created_at}")
            print(f"  Updated: {agent.updated_at}")

            # Get recent versions
            print(f"\n{'='*80}")
            print(f"RECENT VERSIONS (showing up to {limit}):")
            print(f"{'='*80}")

            versions_result = await session.execute(
                text("""
                    SELECT id, version, build_status, error_details, created_at
                    FROM agent_versions
                    WHERE agent_id = :agent_id
                    ORDER BY version DESC
                    LIMIT :limit
                """),
                {"agent_id": agent.id, "limit": limit}
            )

            versions = versions_result.all()
            if not versions:
                print("  (No versions found)")
                return

            for version in versions:
                print(f"\nv{version.version}:")
                print(f"  Build Status: {version.build_status}")
                print(f"  Created: {version.created_at}")

                if version.error_details:
                    error_data = version.error_details

                    # Check if this is a test report
                    if isinstance(error_data, dict) and 'test_report' in error_data:
                        report = error_data['test_report']
                        total = report.get('total', 0)
                        passed = report.get('passed', 0)
                        failed = report.get('failed', 0)

                        print(f"\n  Test Report:")
                        print(f"    Total: {total} | Passed: {passed} | Failed: {failed}")

                        # Show failed tests
                        if failed > 0:
                            print(f"\n  Failed Tests:")
                            for test in report.get('cases', []):
                                if test.get('status') == 'failed':
                                    print(f"\n    ✗ {test.get('name', 'Unknown Test')}")

                                    # Show failed assertions
                                    for assertion in test.get('assertions', []):
                                        if not assertion.get('passed', True):
                                            message = assertion.get('message', 'Unknown error')
                                            print(f"      - {message}")

                                    # Show error message if available
                                    if 'error' in test:
                                        print(f"      Error: {test['error']}")
                    else:
                        # Generic error details
                        print(f"\n  Error Details:")
                        try:
                            error_json = json.dumps(error_data, indent=4)
                            for line in error_json.split('\n'):
                                print(f"    {line}")
                        except (TypeError, ValueError):
                            print(f"    {error_data}")

    finally:
        await engine.dispose()


def main() -> None:
    """Parse CLI arguments and run agent check."""
    parser = argparse.ArgumentParser(
        description="Check agent build status with test report details",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check most recent 3 versions (default)
  python check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1

  # Check most recent 5 versions
  python check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1 --limit 5

  # Check all versions
  python check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1 --limit 999
        """
    )
    parser.add_argument(
        "agent_id",
        help="UUID of the agent to check"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of versions to display (default: 3)"
    )

    args = parser.parse_args()

    try:
        asyncio.run(check_new_agent(args.agent_id, args.limit))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
