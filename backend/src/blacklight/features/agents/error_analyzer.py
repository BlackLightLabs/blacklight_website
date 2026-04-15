"""
Error Analysis Service

Analyzes failed agent builds to extract structured error information
for LLM-based spec revision. Categorizes errors and provides actionable
context for automatic fixes.
"""

from dataclasses import dataclass
from enum import Enum

from src.blacklight.features.agents.models import AgentVersion, BuildStatusEnum


class ErrorCategory(str, Enum):
    """Categories of build/test errors"""

    SPEC_VALIDATION = "spec_validation"
    EDGE_FORMAT = "edge_format"
    TOOL_NOT_FOUND = "tool_not_found"
    STATE_MISMATCH = "state_mismatch"
    TEST_ASSERTION_FAILED = "test_assertion_failed"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """
    Structured analysis of build failure.

    Contains categorized errors and extracted context for LLM revision.
    """

    category: ErrorCategory
    error_messages: list[str]
    affected_components: list[str]  # e.g., ["edges", "node1"]
    suggested_fixes: list[str]
    raw_error_details: dict


class ErrorAnalyzer:
    """
    Analyzes agent build failures to extract structured error information.

    Parses validation errors, test reports, and build logs to categorize
    failures and provide context for automatic spec revision.
    """

    def __init__(self):
        """Initialize error analyzer"""
        pass

    def analyze_build_failure(self, version: AgentVersion) -> ErrorAnalysis:
        """
        Analyze a failed build version to extract error information.

        Args:
            version: Failed AgentVersion with error_details

        Returns:
            ErrorAnalysis with categorized errors and context
        """
        if version.build_status != BuildStatusEnum.FAILED:
            raise ValueError(f"Version {version.id} is not failed (status: {version.build_status})")

        error_details = version.error_details or {}
        error_messages: list[str] = []
        affected_components: list[str] = []
        suggested_fixes: list[str] = []

        # Analyze validation errors
        if "exception" in error_details:
            exception_msg = str(error_details["exception"])
            error_messages.append(exception_msg)

            # Check for edge format errors
            if self._is_edge_format_error(exception_msg):
                return ErrorAnalysis(
                    category=ErrorCategory.EDGE_FORMAT,
                    error_messages=[
                        "Edges use incorrect field names",
                        "Expected: {\"from\": \"node1\", \"to\": \"node2\"}",
                        "Found: {\"from_node\": ..., \"to_node\": ...}",
                    ],
                    affected_components=["edges"],
                    suggested_fixes=[
                        "Rename 'from_node' to 'from' in all edges",
                        "Rename 'to_node' to 'to' in all edges",
                    ],
                    raw_error_details=error_details,
                )

            # Check for tool not found
            if "tool" in exception_msg.lower() and "not found" in exception_msg.lower():
                return ErrorAnalysis(
                    category=ErrorCategory.TOOL_NOT_FOUND,
                    error_messages=[exception_msg],
                    affected_components=self._extract_tool_names(exception_msg),
                    suggested_fixes=["Use only tools from the provided catalog"],
                    raw_error_details=error_details,
                )

            # Check for state field mismatches
            if "state" in exception_msg.lower() and (
                "missing" in exception_msg.lower() or "not found" in exception_msg.lower()
            ):
                return ErrorAnalysis(
                    category=ErrorCategory.STATE_MISMATCH,
                    error_messages=[exception_msg],
                    affected_components=self._extract_state_fields(exception_msg),
                    suggested_fixes=["Ensure all node inputs/outputs reference valid state fields"],
                    raw_error_details=error_details,
                )

            # Check for validation errors
            if "validation" in exception_msg.lower() or "required" in exception_msg.lower():
                return ErrorAnalysis(
                    category=ErrorCategory.SPEC_VALIDATION,
                    error_messages=[exception_msg],
                    affected_components=self._extract_missing_fields(exception_msg),
                    suggested_fixes=["Add missing required fields to spec"],
                    raw_error_details=error_details,
                )

        # Analyze test failures
        if "test_report" in error_details:
            test_report = error_details["test_report"]
            failed_tests = []

            for test_case in test_report.get("cases", []):
                if test_case.get("status") != "passed":
                    test_name = test_case.get("name", "unnamed")
                    failed_tests.append(test_name)
                    error_messages.append(f"Test '{test_name}' failed")

                    # Extract assertion failures
                    for assertion in test_case.get("assertions", []):
                        if not assertion.get("passed"):
                            error_messages.append(f"  - {assertion.get('message', 'Unknown error')}")

            if failed_tests:
                return ErrorAnalysis(
                    category=ErrorCategory.TEST_ASSERTION_FAILED,
                    error_messages=error_messages,
                    affected_components=failed_tests,
                    suggested_fixes=["Review test assertions and mocks", "Ensure agent behavior matches test expectations"],
                    raw_error_details=error_details,
                )

        # Syntax errors
        if "error" in error_details and "syntax" in str(error_details.get("error", "")).lower():
            return ErrorAnalysis(
                category=ErrorCategory.SYNTAX_ERROR,
                error_messages=[error_details.get("error", "Syntax validation failed")],
                affected_components=["generated_code"],
                suggested_fixes=["Check for invalid Python syntax in spec"],
                raw_error_details=error_details,
            )

        # Timeout
        if "timeout" in str(error_details).lower():
            return ErrorAnalysis(
                category=ErrorCategory.TIMEOUT,
                error_messages=["Execution exceeded time limit"],
                affected_components=["runtime"],
                suggested_fixes=["Reduce max_steps or increase timeout_seconds"],
                raw_error_details=error_details,
            )

        # Unknown error
        return ErrorAnalysis(
            category=ErrorCategory.UNKNOWN,
            error_messages=error_messages or ["Unknown build failure"],
            affected_components=[],
            suggested_fixes=["Review error details manually"],
            raw_error_details=error_details,
        )

    def _is_edge_format_error(self, error_msg: str) -> bool:
        """Check if error is related to edge field names"""
        return (
            "from_node" in error_msg or
            "to_node" in error_msg or
            ("edge" in error_msg.lower() and "field" in error_msg.lower())
        )

    def _extract_tool_names(self, error_msg: str) -> list[str]:
        """Extract tool names from error message"""
        # Simple heuristic - look for quoted strings near "tool"
        import re
        tools = re.findall(r"tool[:\s]+['\"]([^'\"]+)['\"]", error_msg, re.IGNORECASE)
        return tools

    def _extract_state_fields(self, error_msg: str) -> list[str]:
        """Extract state field names from error message"""
        import re
        fields = re.findall(r"field[:\s]+['\"]([^'\"]+)['\"]", error_msg, re.IGNORECASE)
        return fields

    def _extract_missing_fields(self, error_msg: str) -> list[str]:
        """Extract missing field names from validation error"""
        import re
        fields = re.findall(r"['\"]([^'\"]+)['\"].*required", error_msg, re.IGNORECASE)
        return fields

    def format_for_llm(self, analysis: ErrorAnalysis) -> str:
        """
        Format error analysis as a human-readable string for LLM context.

        Args:
            analysis: ErrorAnalysis to format

        Returns:
            Formatted error description
        """
        lines = []
        lines.append(f"Error Category: {analysis.category.value}")
        lines.append("")
        lines.append("Error Messages:")
        for msg in analysis.error_messages:
            lines.append(f"  - {msg}")

        if analysis.affected_components:
            lines.append("")
            lines.append("Affected Components:")
            for component in analysis.affected_components:
                lines.append(f"  - {component}")

        if analysis.suggested_fixes:
            lines.append("")
            lines.append("Suggested Fixes:")
            for fix in analysis.suggested_fixes:
                lines.append(f"  - {fix}")

        return "\n".join(lines)
