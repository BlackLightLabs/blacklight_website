#!/usr/bin/env python3
"""
Check agent status, versions, and build logs in the database.

Usage:
    python check_agent_status.py <agent_id>
    python check_agent_status.py --help

Example:
    python check_agent_status.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.blacklight.common.settings import settings


async def check_agent(agent_id: str) -> None:
    """
    Check agent status and build history.

    Args:
        agent_id: UUID of the agent to check

    Raises:
        ValueError: If agent_id is not a valid UUID format
    """
    # Create async engine
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

            print(f"✓ Agent found")
            print(f"  ID: {agent.id}")
            print(f"  Status: {agent.status}")
            print(f"  Description: {agent.description}")
            print(f"  Created: {agent.created_at}")
            print(f"  Updated: {agent.updated_at}")

            # Get versions
            print(f"\nVersions:")
            versions_result = await session.execute(
                text("""
                    SELECT version, status, error_message, created_at
                    FROM agent_versions
                    WHERE agent_id = :agent_id
                    ORDER BY version DESC
                """),
                {"agent_id": agent.id}
            )

            versions = versions_result.all()
            if versions:
                for version in versions:
                    error_msg = version.error_message if version.error_message else "OK"
                    print(f"  v{version.version}: {version.status} - {error_msg} ({version.created_at})")
            else:
                print("  (No versions found)")

            # Get build logs
            print(f"\nRecent Build Logs (last 20):")
            build_logs_result = await session.execute(
                text("""
                    SELECT version, phase, status, error_message, created_at
                    FROM agent_build_logs
                    WHERE agent_id = :agent_id
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
                {"agent_id": agent.id}
            )

            logs = build_logs_result.all()
            if logs:
                for log in logs:
                    status_icon = "✓" if log.status == "success" else "✗"
                    print(f"  {status_icon} v{log.version} - {log.phase}: {log.status}")
                    if log.error_message:
                        # Truncate long error messages
                        error_preview = log.error_message[:200]
                        if len(log.error_message) > 200:
                            error_preview += "..."
                        print(f"      Error: {error_preview}")
            else:
                print("  (No build logs found)")

    finally:
        await engine.dispose()


def main() -> None:
    """Parse CLI arguments and run agent status check."""
    parser = argparse.ArgumentParser(
        description="Check agent status, versions, and build logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_agent_status.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
  python check_agent_status.py eda928ab-c3e4-466c-9a45-526d8835c2b1
        """
    )
    parser.add_argument(
        "agent_id",
        help="UUID of the agent to check"
    )

    args = parser.parse_args()

    try:
        asyncio.run(check_agent(args.agent_id))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
