"""
CLI runner for Simple Adder

Usage:
    python run.py --input '{"field": "value"}'
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import app, AgentState


def run_agent(initial_state: dict) -> dict:
    """
    Execute the agent with the given initial state.

    Args:
        initial_state: Initial state dictionary

    Returns:
        Final state after execution
    """
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Simple Adder")
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

        # Run sync agent
        final_state = run_agent(initial_state)

        print("Final state:")
        print(json.dumps(final_state, indent=2))

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during execution: {e}", file=sys.stderr)
        sys.exit(1)