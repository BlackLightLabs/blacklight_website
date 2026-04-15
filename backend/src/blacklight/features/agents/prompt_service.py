"""
Prompt Service

Manages prompt templates with database storage, Jinja2 rendering, and caching.
Supports system prompts, user overrides, and versioned templates.
"""

import json
from functools import lru_cache
from typing import Any

from jinja2 import Template, TemplateError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blacklight.features.agents.models import PromptTemplate, PromptTemplateType


class PromptRenderError(Exception):
    """Raised when template rendering fails"""

    pass


class PromptService:
    """
    Service for loading and rendering prompt templates.

    Supports:
    - Database-backed templates
    - Jinja2 template rendering
    - User-specific overrides (from UserSettings.custom_prompts)
    - Template caching for performance
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize prompt service.

        Args:
            db: Async database session
        """
        self.db = db
        self._cache: dict[str, str] = {}

    async def get_template(
        self, name: str, template_type: PromptTemplateType = PromptTemplateType.SYSTEM
    ) -> str:
        """
        Load a template by name and type.

        Args:
            name: Template name (e.g., "agent_creation_system")
            template_type: Type of template

        Returns:
            Template content

        Raises:
            ValueError: If template not found
        """
        # Check cache first
        cache_key = f"{template_type.value}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Query database
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .where(PromptTemplate.template_type == template_type)
            .where(PromptTemplate.is_active == 1)
            .order_by(PromptTemplate.version.desc())
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(
                f"Template '{name}' of type '{template_type.value}' not found in database"
            )

        # Cache and return
        self._cache[cache_key] = template.content
        return template.content

    async def render_template(
        self,
        name: str,
        variables: dict[str, Any],
        template_type: PromptTemplateType = PromptTemplateType.SYSTEM,
        user_override: str | None = None,
    ) -> str:
        """
        Render a template with variables.

        Args:
            name: Template name
            variables: Variables to inject into template
            template_type: Type of template
            user_override: Optional user-provided template override

        Returns:
            Rendered prompt text

        Raises:
            PromptRenderError: If rendering fails
        """
        try:
            # Use user override if provided, otherwise load from DB
            if user_override:
                template_content = user_override
            else:
                template_content = await self.get_template(name, template_type)

            # Render with Jinja2
            template = Template(template_content)
            rendered = template.render(**variables)

            return rendered

        except TemplateError as e:
            raise PromptRenderError(f"Failed to render template '{name}': {e}") from e
        except Exception as e:
            raise PromptRenderError(f"Unexpected error rendering template '{name}': {e}") from e

    async def get_user_override(
        self, user_id: int, prompt_name: str
    ) -> str | None:
        """
        Get user-specific prompt override from UserSettings.

        Args:
            user_id: User ID
            prompt_name: Name of prompt to override

        Returns:
            User's custom prompt or None
        """
        from src.blacklight.features.auth.models import UserSettings

        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings and settings.custom_prompts:
            return settings.custom_prompts.get(prompt_name)

        return None

    async def create_template(
        self,
        name: str,
        content: str,
        template_type: PromptTemplateType,
        description: str | None = None,
        variables: dict[str, str] | None = None,
        created_by: int | None = None,
    ) -> PromptTemplate:
        """
        Create a new prompt template.

        Args:
            name: Unique template name
            content: Template content (Jinja2 syntax)
            template_type: Type of template
            description: Human-readable description
            variables: Expected variables dict
            created_by: User ID who created (None for system)

        Returns:
            Created template

        Raises:
            ValueError: If template already exists
        """
        import uuid

        from src.blacklight.features.agents.models import PromptTemplate

        # Check if template exists
        existing = await self.get_template_by_name(name, template_type, active_only=False)
        if existing:
            raise ValueError(f"Template '{name}' already exists")

        # Create template
        template = PromptTemplate(
            id=str(uuid.uuid4()),
            name=name,
            template_type=template_type,
            content=content,
            description=description,
            variables=variables,
            created_by=created_by,
        )

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        # Clear cache
        self._cache.clear()

        return template

    async def get_template_by_name(
        self,
        name: str,
        template_type: PromptTemplateType,
        active_only: bool = True,
    ) -> PromptTemplate | None:
        """
        Get template object by name.

        Args:
            name: Template name
            template_type: Template type
            active_only: Only return active templates

        Returns:
            Template or None
        """
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .where(PromptTemplate.template_type == template_type)
        )

        if active_only:
            stmt = stmt.where(PromptTemplate.is_active == 1)

        stmt = stmt.order_by(PromptTemplate.version.desc())

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def clear_cache(self):
        """Clear template cache (useful after updates)"""
        self._cache.clear()


# Fallback system prompts (used if DB templates not found)
FALLBACK_AGENT_CREATION_PROMPT = """You are an AI agent systems engineer. Your job is to design agent specifications that will be compiled into working LangGraph agents.

{{tool_catalog}}

SPECIFICATION FORMAT:
You MUST respond with "AGENT_READY:" followed by a JSON object conforming to this schema:
{
  "name": "descriptive name",
  "description": "what the agent does",
  "model": "qwen/qwen3-coder-30b",
  "state": [{"name": "field", "type": "str", "description": "..."}],
  "nodes": [
    {"id": "node1", "type": "tool", "tool": "search_kb", "input": ["query"], "output": ["results"]}
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
6. Use "from" and "to" fields in edges, NOT "from_node" and "to_node"

GOOD EXAMPLE:
{{example_spec}}

Be conversational and helpful. Ask clarifying questions about:
- What the agent should do
- What tools it needs
- What the expected behavior is
- How to test it

When you have enough information, emit AGENT_READY: with the complete spec."""


FALLBACK_REVISION_PROMPT = """You are an AI agent systems engineer reviewing a failed agent build.

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
