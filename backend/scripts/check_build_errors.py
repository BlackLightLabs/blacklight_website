#!/usr/bin/env python3
"""
Check agent build errors and detailed build logs.

Usage:
    python check_build_errors.py <agent_id>
    python check_build_errors.py --help

Example:
    python check_build_errors.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
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


async def check_build_errors(agent_id: str) -> None:
    """
    Check agent build errors and detailed build logs.

    Args:
        agent_id: UUID of the agent to check

    Displays:
        - Agent basic info
        - All versions with build status and error details
        - Detailed build logs per version
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
                    SELECT id, status, description, created_at
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

            # Get versions with build errors
            print(f"\n{'='*80}")
            print("VERSIONS:")
            print(f"{'='*80}")

            versions_result = await session.execute(
                text("""
                    SELECT id, version, build_status, error_details, created_at
                    FROM agent_versions
                    WHERE agent_id = :agent_id
                    ORDER BY version DESC
                """),
                {"agent_id": agent.id}
            )

            versions = versions_result.all()
            if not versions:
                print("  (No versions found)")
                return

            version_ids = []
            for version in versions:
                print(f"\nv{version.version}:")
                print(f"  ID: {version.id}")
                print(f"  Build Status: {version.build_status}")
                print(f"  Created: {version.created_at}")

                if version.error_details:
                    print(f"  Error Details:")
                    try:
                        error_json = json.dumps(version.error_details, indent=4)
                        # Indent each line
                        for line in error_json.split('\n'):
                            print(f"    {line}")
                    except (TypeError, ValueError):
                        print(f"    {version.error_details}")

                version_ids.append(version.id)

            # Get build logs for each version
            print(f"\n{'='*80}")
            print("BUILD LOGS:")
            print(f"{'='*80}")

            for version_id in version_ids:
                logs_result = await session.execute(
                    text("""
                        SELECT stage, level, message, created_at
                        FROM agent_build_logs
                        WHERE agent_version_id = :version_id
                        ORDER BY created_at ASC
                    """),
                    {"version_id": version_id}
                )

                logs = list(logs_result)
                if logs:
                    print(f"\nVersion {version_id}:")
                    for log in logs:
                        # Icon based on log level
                        icon = {
                            "INFO": "✓",
                            "WARN": "⚠",
                            "WARNING": "⚠",
                            "ERROR": "✗",
                            "CRITICAL": "✗"
                        }.get(log.level, "•")

                        # Truncate long messages
                        message = log.message
                        if len(message) > 200:
                            message_preview = message[:200] + "..."
                            print(f"  {icon} [{log.stage}] [{log.level}] {message_preview}")
                            print(f"     ... (truncated, full length: {len(log.message)} chars)")
                        else:
                            print(f"  {icon} [{log.stage}] [{log.level}] {message}")

    finally:
        await engine.dispose()


def main() -> None:
    """Parse CLI arguments and run build error check."""
    parser = argparse.ArgumentParser(
        description="Check agent build errors and detailed build logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_build_errors.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
  python check_build_errors.py eda928ab-c3e4-466c-9a45-526d8835c2b1
        """
    )
    parser.add_argument(
        "agent_id",
        help="UUID of the agent to check"
    )

    args = parser.parse_args()

    try:
        asyncio.run(check_build_errors(args.agent_id))
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
