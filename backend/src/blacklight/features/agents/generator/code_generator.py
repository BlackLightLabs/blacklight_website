"""
Code Generator Service

Generates LangGraph agent code from AgentSpec using Jinja2 templates.
Creates a complete Python module with graph, tools, and test runner.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template

from src.blacklight.features.agents.spec_schema import AgentSpec


class CodeGenerationError(Exception):
    """Raised when code generation fails"""

    pass


class CodeGenerator:
    """
    Generates Python code from agent specifications.

    Uses Jinja2 templates to create a complete, importable Python module
    containing the LangGraph workflow, tool wrappers, and test runner.
    """

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize the code generator.

        Args:
            templates_dir: Path to Jinja2 templates directory
                          (defaults to generator/templates)
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"

        self.templates_dir = templates_dir

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["tojson"] = self._tojson_filter

    def _tojson_filter(self, value: Any) -> str:
        """Custom JSON filter for templates"""
        import json
        return json.dumps(value, indent=2)

    def generate(
        self,
        spec: AgentSpec,
        output_dir: Path,
        version: int = 1,
    ) -> Path:
        """
        Generate agent code from specification.

        Creates a complete Python module at:
        output_dir/{agent_id}/v{version}/

        Args:
            spec: Validated agent specification
            output_dir: Base output directory
            version: Version number for this build

        Returns:
            Path to the generated module directory

        Raises:
            CodeGenerationError: If generation fails
        """
        try:
            # Create output directory
            module_dir = output_dir / f"v{version}"
            module_dir.mkdir(parents=True, exist_ok=True)

            # Template context
            context = {
                "spec": spec,
                "version": version,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Generate files from templates
            self._render_template("graph.py.j2", module_dir / "graph.py", context)
            self._render_template("tools.py.j2", module_dir / "tools.py", context)
            self._render_template("__init__.py.j2", module_dir / "__init__.py", context)
            self._render_template("run.py.j2", module_dir / "run.py", context)

            # Make run.py executable
            (module_dir / "run.py").chmod(0o755)

            return module_dir

        except Exception as e:
            raise CodeGenerationError(f"Failed to generate code: {e}") from e

    def _render_template(self, template_name: str, output_path: Path, context: dict):
        """
        Render a Jinja2 template to a file.

        Args:
            template_name: Name of the template file
            output_path: Path where rendered output should be written
            context: Template context dictionary
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)

            # Write to file
            output_path.write_text(rendered)

        except Exception as e:
            raise CodeGenerationError(
                f"Failed to render template '{template_name}': {e}"
            ) from e

    def validate_syntax(self, module_dir: Path) -> tuple[bool, str]:
        """
        Validate that generated Python code has valid syntax.

        Args:
            module_dir: Path to generated module directory

        Returns:
            Tuple of (is_valid, error_message)
        """
        import ast
        import traceback

        python_files = ["graph.py", "tools.py", "__init__.py", "run.py"]

        for filename in python_files:
            file_path = module_dir / filename
            if not file_path.exists():
                return False, f"Missing file: {filename}"

            try:
                code = file_path.read_text()
                ast.parse(code)
            except SyntaxError as e:
                return False, f"Syntax error in {filename}:{e.lineno}: {e.msg}"
            except Exception as e:
                return False, f"Error parsing {filename}: {str(e)}\n{traceback.format_exc()}"

        return True, "All files have valid syntax"

    def generate_test_file(
        self, spec: AgentSpec, output_dir: Path, version: int = 1
    ) -> Path:
        """
        Generate a test file for the agent.

        Args:
            spec: Agent specification
            output_dir: Output directory
            version: Version number

        Returns:
            Path to generated test file
        """
        module_dir = output_dir / f"v{version}"
        test_file = module_dir / "test_agent.py"

        # Generate test code
        test_code = self._generate_test_code(spec)
        test_file.write_text(test_code)

        return test_file

    def _generate_test_code(self, spec: AgentSpec) -> str:
        """Generate pytest code for agent tests"""
        lines = [
            '"""',
            f"Tests for {spec.name}",
            "",
            "Auto-generated test file",
            '"""',
            "",
            "import json",
            "import pytest",
            "from graph import app, AgentState",
            "from tools import set_mock_response, grant_approval, clear_mocks",
            "",
            "",
        ]

        # Generate test functions
        for i, test_case in enumerate(spec.tests):
            lines.extend([
                f"def test_{test_case.name.replace(' ', '_')}():",
                f'    """Test: {test_case.name}"""',
                "    clear_mocks()",
                "",
            ])

            # Set up mocks
            if test_case.mocks:
                lines.append("    # Set up mocks")
                for tool_name, mock_response in test_case.mocks.items():
                    lines.append(
                        f"    set_mock_response('{tool_name}', {json.dumps(mock_response)})"
                    )
                    # Grant approval if needed
                    tool_spec = next((t for t in spec.tools if t.name == tool_name), None)
                    if tool_spec and tool_spec.requires_approval:
                        lines.append(f"    grant_approval('{tool_name}')")
                lines.append("")

            # Set initial state
            lines.extend([
                "    # Initial state",
                f"    initial_state = {json.dumps(test_case.input, indent=4)}",
                "",
                "    # Run agent",
                "    final_state = app.invoke(initial_state)",
                "",
            ])

            # Add assertions
            for assertion in test_case.assertions:
                if assertion.type.value == "state_contains":
                    lines.append(
                        f"    assert '{assertion.path}' in final_state, "
                        f"'State should contain {assertion.path}'"
                    )
                    if assertion.value is not None:
                        lines.append(
                            f"    assert final_state['{assertion.path}'] == {repr(assertion.value)}"
                        )

            lines.append("")

        return "\n".join(lines)
