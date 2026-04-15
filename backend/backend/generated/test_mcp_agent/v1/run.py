"""
CLI runner for WebTesterAgent

Usage:
    python run.py --input '{"field": "value"}'
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import get_app, AgentState
from tools import shutdown_mcp_tools


async def run_agent(initial_state: dict) -> dict:
    """
    Execute the agent with the given initial state.

    For agents with MCP tools, this initializes the MCP client first.

    Args:
        initial_state: Initial state dictionary

    Returns:
        Final state after execution
    """
    try:
        # Get app with MCP tools initialized
        app = await get_app()

        # Execute agent
        result = await app.ainvoke(initial_state)
        return result
    finally:
        # Cleanup MCP resources
        await shutdown_mcp_tools()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run WebTesterAgent")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Initial state as JSON string"
    )

    args = parser.parse_args()

    try:
        initial_state = json.loads(args.input)
        print("Running agent with initial state:")
        print(json.dumps(initial_state, indent=2))
        print("\n" + "="*60 + "\n")

        # Run async agent with MCP tools
        final_state = asyncio.run(run_agent(initial_state))

        print("Final state:")
        print(json.dumps(final_state, indent=2))

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during execution: {e}", file=sys.stderr)
        sys.exit(1)