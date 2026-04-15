"""
Spec Revision Service

Uses LLM to automatically revise failed agent specifications based on
error analysis. Renders revision prompts and parses corrected specs.
"""

import json
import re
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.blacklight.common.llm_config import LLMConfig
from src.blacklight.features.agents.error_analyzer import ErrorAnalysis, ErrorAnalyzer
from src.blacklight.features.agents.models import PromptTemplateType
from src.blacklight.features.agents.prompt_service import PromptService


class SpecRevisionError(Exception):
    """Raised when spec revision fails"""

    pass


class SpecReviser:
    """
    Revises failed agent specifications using LLM-based error correction.

    Uses the agent_revision_system prompt template to guide the LLM in
    fixing spec errors based on build/test failures.
    """

    def __init__(self, prompt_service: PromptService, error_analyzer: ErrorAnalyzer):
        """
        Initialize spec reviser.

        Args:
            prompt_service: Service for loading prompt templates
            error_analyzer: Service for analyzing build failures
        """
        self.prompt_service = prompt_service
        self.error_analyzer = error_analyzer
        self.llm = LLMConfig.get_llm()

    async def revise_spec(
        self,
        original_spec: dict[str, Any],
        error_analysis: ErrorAnalysis,
        attempt_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Revise a failed spec using LLM with error context.

        Args:
            original_spec: The original (failed) agent specification
            error_analysis: Structured error analysis from ErrorAnalyzer
            attempt_history: Previous revision attempts (for context)

        Returns:
            Revised spec dictionary

        Raises:
            SpecRevisionError: If revision fails or LLM doesn't return valid spec
        """
        # Format error analysis for LLM
        error_text = self.error_analyzer.format_for_llm(error_analysis)

        # Format previous attempts
        previous_attempts_text = self._format_attempt_history(attempt_history or [])

        # Render revision prompt
        try:
            system_prompt = await self.prompt_service.render_template(
                name="agent_revision_system",
                variables={
                    "original_spec": json.dumps(original_spec, indent=2),
                    "errors": error_text,
                    "previous_attempts": previous_attempts_text,
                },
                template_type=PromptTemplateType.REVISION,
            )
        except Exception as e:
            raise SpecRevisionError(f"Failed to render revision prompt: {e}") from e

        # Build messages for LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Please fix the specification. The main issue is: {error_analysis.category.value}"
            ),
        ]

        # Call LLM
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content
        except Exception as e:
            raise SpecRevisionError(f"LLM API call failed: {e}") from e

        # Parse revised spec from response
        revised_spec = self._parse_revised_spec(response_text)

        if not revised_spec:
            raise SpecRevisionError(
                "LLM did not return a valid revised spec. "
                f"Response: {response_text[:200]}..."
            )

        return revised_spec

    def _parse_revised_spec(self, response_text: str) -> dict[str, Any] | None:
        """
        Parse revised spec from LLM response.

        Expects "AGENT_REVISED:" marker followed by JSON.

        Args:
            response_text: LLM response text

        Returns:
            Parsed spec dict or None if not found
        """
        # Look for AGENT_REVISED: marker
        if "AGENT_REVISED:" not in response_text:
            # Try to find JSON anyway
            return self._extract_json_from_text(response_text)

        # Extract JSON after marker
        marker_pos = response_text.index("AGENT_REVISED:")
        json_text = response_text[marker_pos + len("AGENT_REVISED:") :]

        return self._extract_json_from_text(json_text)

    def _extract_json_from_text(self, text: str) -> dict[str, Any] | None:
        """
        Extract JSON object from text.

        Args:
            text: Text potentially containing JSON

        Returns:
            Parsed JSON dict or None
        """
        try:
            # Find first { and last }
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]

            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return None

    def _format_attempt_history(self, attempt_history: list[dict]) -> str:
        """
        Format previous revision attempts for LLM context.

        Args:
            attempt_history: List of previous attempts with errors

        Returns:
            Formatted text describing previous attempts
        """
        if not attempt_history:
            return "No previous attempts."

        lines = []
        for i, attempt in enumerate(attempt_history, 1):
            lines.append(f"Attempt {i}:")
            lines.append(f"  Error: {attempt.get('error_category', 'unknown')}")
            lines.append(f"  Issue: {attempt.get('error_summary', 'N/A')}")

        return "\n".join(lines)

    async def quick_fix_edge_format(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        Apply quick fix for edge format errors without LLM.

        Renames 'from_node' → 'from' and 'to_node' → 'to' in all edges.

        Args:
            spec: Spec with incorrect edge format

        Returns:
            Spec with corrected edge format
        """
        fixed_spec = spec.copy()

        if "edges" in fixed_spec:
            fixed_edges = []
            for edge in fixed_spec["edges"]:
                fixed_edge = {}

                # Rename from_node → from
                if "from_node" in edge:
                    fixed_edge["from"] = edge["from_node"]
                elif "from" in edge:
                    fixed_edge["from"] = edge["from"]

                # Rename to_node → to
                if "to_node" in edge:
                    fixed_edge["to"] = edge["to_node"]
                elif "to" in edge:
                    fixed_edge["to"] = edge["to"]

                # Copy other fields
                for key, value in edge.items():
                    if key not in ["from_node", "to_node", "from", "to"]:
                        fixed_edge[key] = value

                fixed_edges.append(fixed_edge)

            fixed_spec["edges"] = fixed_edges

        return fixed_spec
