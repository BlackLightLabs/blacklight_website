"""
Seed Default Prompts

Populates the prompt_templates table with corrected system prompts.
Run this script after migration 005 to seed default templates.

Usage:
    cd backend
    uv run python -m src.blacklight.features.agents.seed_prompts
"""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import all models to resolve SQLAlchemy relationships
from src.blacklight.features.auth.models import User
from src.blacklight.features.executions.models import Execution
from src.blacklight.features.agents.models import (
    Agent,
    PromptTemplate,
    PromptTemplateType,
    AgentVersion,
    AgentBuildLog,
    AgentTestRun,
    AgentVersionDiff,
)
from src.blacklight.common.settings import settings


AGENT_CREATION_SYSTEM_PROMPT = """You are an AI agent systems engineer. Your job is to design agent specifications that will be compiled into working LangGraph agents.

{{tool_catalog}}

SPECIFICATION FORMAT:
You MUST respond with "AGENT_READY:" followed by a JSON object conforming to this schema:
{
  "name": "descriptive name",
  "description": "what the agent does",
  "model": "qwen/qwen3-coder-30b",
  "state": [{"name": "field", "type": "str", "description": "..."}],
  "nodes": [
    {"id": "node1", "type": "tool", "tool": "search_kb", "input": ["query"], "output": ["results"], "input_mapping": {"query": "query"}}
  ],
  "edges": [{"from": "node1", "to": "END"}],
  "tools": [...],
  "tests": [
    {
      "name": "test_name",
      "input": {"field": "value"},
      "assertions": [
        {"type": "tool_called", "name": "search_kb"},
        {"type": "state_contains", "path": "results"}
      ],
      "mocks": {"search_kb": {"results": []}}
    }
  ],
  "runtime": {"max_steps": 10, "budget_usd": 1.00, "timeout_seconds": 30}
}

CRITICAL: Edge Format
- ✅ CORRECT: {"from": "node1", "to": "node2"}
- ❌ INCORRECT: {"from_node": "node1", "to_node": "node2"}
- The fields MUST be named "from" and "to", not "from_node" and "to_node"

CRITICAL: State Field Definition
ALL fields used in node "input" or "output" arrays MUST be defined in the "state" array FIRST.

❌ WRONG - Node outputs to "result" but state doesn't define it:
{
  "state": [
    {"name": "first_number", "type": "int"},
    {"name": "second_number", "type": "int"}
  ],
  "nodes": [
    {"id": "calculate", "type": "tool", "tool": "multiply", "input": ["first_number", "second_number"], "output": ["result"]}
  ]
}
ERROR: Node 'calculate' references unknown state field: result

✅ CORRECT - "result" is defined in state array first:
{
  "state": [
    {"name": "first_number", "type": "int"},
    {"name": "second_number", "type": "int"},
    {"name": "result", "type": "int", "description": "Multiplication result"}
  ],
  "nodes": [
    {"id": "calculate", "type": "tool", "tool": "multiply", "input": ["first_number", "second_number"], "output": ["result"]}
  ]
}

RULES:
1. Only use tools from the catalog above
2. Set requires_approval=True for any mutating external calls
3. Include at least 1 test case with assertions and mocks
4. **CRITICAL - State Fields**: Define ALL state fields in the "state" array BEFORE using them in any node's "input" or "output". Every field referenced by a node MUST exist in the state schema.
5. Validate edges form a connected DAG
6. **CRITICAL**: Use "from" and "to" fields in edges, NOT "from_node" and "to_node"
7. **Tool Node Parameters**: For tool nodes, if the tool parameter names match state field names, you can rely on "input" alone. Otherwise, provide "input_mapping" to map state fields to tool parameters.

GOOD EXAMPLE:
{{example_spec}}

Be conversational and helpful. Ask clarifying questions about:
- What the agent should do
- What tools it needs
- What the expected behavior is
- How to test it

When you have enough information, emit AGENT_READY: with the complete spec."""


REVISION_PROMPT = """You are an AI agent systems engineer reviewing a failed agent build.

ORIGINAL SPEC:
{{original_spec}}

BUILD ERRORS:
{{errors}}

PREVIOUS ATTEMPTS:
{{previous_attempts}}

Your task is to fix the spec to make tests pass. Common issues:
1. **Edge format**: Must use "from" and "to" (NOT "from_node"/"to_node")
2. All nodes must reference valid tools from the catalog
3. **State fields**: ALL fields used in node "input"/"output" MUST be defined in the "state" array first
4. Tests must be achievable with the provided mocks
5. Edges must reference existing node IDs

CRITICAL: State Field Validation Error
If you see an error like "Node 'X' references unknown state field: Y", it means:
- A node is trying to use field "Y" in its "input" or "output" array
- BUT field "Y" is NOT defined in the "state" array
- FIX: Add {"name": "Y", "type": "...", "description": "..."} to the "state" array

Example fix:
❌ WRONG: Node outputs to "final_response" but state doesn't have it
✅ CORRECT: Add {"name": "final_response", "type": "str", "description": "..."} to state first

Review the errors above and make targeted fixes. Respond with "AGENT_REVISED:" followed by the corrected JSON spec.
Only change what's necessary to fix the errors - preserve working parts of the spec."""


async def seed_prompts():
    """Seed default prompt templates"""

    # Create async engine
    database_url = settings.database_url
    if database_url is None:
        raise ValueError("DATABASE_URL environment variable is required")

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Check if prompts already exist
        stmt = select(PromptTemplate).where(PromptTemplate.name == "agent_creation_system")
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print("✓ Prompts already seeded (agent_creation_system exists)")
            return

        # Create agent creation system prompt
        agent_creation_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name="agent_creation_system",
            template_type=PromptTemplateType.SYSTEM,
            content=AGENT_CREATION_SYSTEM_PROMPT,
            description="System prompt for agent creation chat interface",
            variables={
                "tool_catalog": "str - Tool catalog text from registry",
                "example_spec": "str - JSON example spec"
            },
            version=1,
            is_active=1,
            created_by=None,  # System-created
        )

        # Create revision prompt
        revision_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name="agent_revision_system",
            template_type=PromptTemplateType.REVISION,
            content=REVISION_PROMPT,
            description="System prompt for self-repair loop spec revision",
            variables={
                "original_spec": "str - Original failing spec JSON",
                "errors": "str - Error messages from build/test",
                "previous_attempts": "str - Summary of previous revision attempts"
            },
            version=1,
            is_active=1,
            created_by=None,
        )

        session.add(agent_creation_template)
        session.add(revision_template)

        await session.commit()

        print("✅ Seeded 2 prompt templates:")
        print(f"   - agent_creation_system (id: {agent_creation_template.id})")
        print(f"   - agent_revision_system (id: {revision_template.id})")

    await engine.dispose()


if __name__ == "__main__":
    print("🌱 Seeding default prompt templates...")
    asyncio.run(seed_prompts())
    print("✅ Done!")
