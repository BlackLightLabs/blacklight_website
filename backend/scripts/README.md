# Backend Utility Scripts

This directory contains utility scripts for database inspection, debugging, and maintenance tasks.

## Prerequisites

All scripts require:
- Python 3.10+
- Active database connection (configured in `../.env`)
- Backend dependencies installed (`uv sync`)

## Available Scripts

### check_agent_status.py

Check agent status, versions, and build logs.

**Usage:**
```bash
cd backend
uv run python scripts/check_agent_status.py <agent_id>
```

**Example:**
```bash
uv run python scripts/check_agent_status.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
```

**Output:**
- Agent ID, status, description, timestamps
- All versions with build status
- Recent build logs (last 20 entries)

---

### check_build_errors.py

Check detailed agent build errors and build logs.

**Usage:**
```bash
cd backend
uv run python scripts/check_build_errors.py <agent_id>
```

**Example:**
```bash
uv run python scripts/check_build_errors.py 59f2d0fe-a53c-4aed-8fa4-ce6792f00919
```

**Output:**
- Agent basic info
- All versions with build status and error details (full JSON)
- Complete build logs for each version (stage, level, message)

**Best For:**
- Debugging build failures
- Understanding error details
- Viewing full build pipeline logs

---

### check_new_agent.py

Check agent build status with test report details.

**Usage:**
```bash
cd backend
uv run python scripts/check_new_agent.py <agent_id> [--limit N]
```

**Examples:**
```bash
# Check last 3 versions (default)
uv run python scripts/check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1

# Check last 5 versions
uv run python scripts/check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1 --limit 5

# Check all versions
uv run python scripts/check_new_agent.py eda928ab-c3e4-466c-9a45-526d8835c2b1 --limit 999
```

**Output:**
- Agent basic info
- Recent versions (configurable limit)
- Detailed test reports (passed/failed counts)
- Failed test details with assertions

**Best For:**
- Viewing test results
- Understanding why agents failed verification
- Debugging test assertion failures

---

## Common Workflows

### 1. Check if Agent Built Successfully
```bash
cd backend
uv run python scripts/check_agent_status.py <agent_id>
```
Look for `Status: READY` in the output.

### 2. Debug Build Failure
```bash
cd backend
# First, check general status
uv run python scripts/check_agent_status.py <agent_id>

# Then, check detailed build errors
uv run python scripts/check_build_errors.py <agent_id>
```

### 3. Debug Test Failures
```bash
cd backend
uv run python scripts/check_new_agent.py <agent_id> --limit 5
```
Look for "Failed Tests" section to see which tests failed and why.

---

## Script Development Guidelines

When adding new utility scripts to this directory:

1. **Use argparse** for CLI argument parsing (no hardcoded IDs)
2. **Add docstrings** to all functions (Google style)
3. **Include usage examples** in module docstring
4. **Handle errors gracefully** with try/except and exit codes
5. **Add to this README** with usage examples
6. **Make executable** with `chmod +x script_name.py`
7. **Add shebang** `#!/usr/bin/env python3` at the top

**Example Script Structure:**
```python
#!/usr/bin/env python3
"""
Brief description of what the script does.

Usage:
    python script_name.py <arg1> [--option]
    python script_name.py --help

Example:
    python script_name.py abc123
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.blacklight.common.settings import settings


async def main_function(arg1: str) -> None:
    """Function docstring with Args and Returns."""
    pass


def main() -> None:
    """Parse CLI arguments and run main function."""
    parser = argparse.ArgumentParser(
        description="Script description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("arg1", help="Argument description")
    args = parser.parse_args()

    try:
        asyncio.run(main_function(args.arg1))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Notes

- All scripts use **async database connections** (asyncpg)
- Database URL is read from `.env` via `settings.database_url`
- Scripts automatically convert `postgresql://` to `postgresql+asyncpg://`
- Exit codes: 0 (success), 1 (error), 130 (interrupted by user)
