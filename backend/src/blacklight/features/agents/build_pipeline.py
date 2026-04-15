"""
Agent Build Pipeline

Orchestrates the complete agent build flow from specification
to ready-to-use compiled agent with validated tests.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from src.blacklight.features.agents.error_analyzer import ErrorAnalyzer, ErrorCategory
from src.blacklight.features.agents.generator.code_generator import (
    CodeGenerator,
    CodeGenerationError,
)
from src.blacklight.features.agents.models import BuildStatusEnum
from src.blacklight.features.agents.repositories import (
    AgentRepository,
    AgentVersionRepository,
    AgentBuildLogRepository,
    AgentTestRunRepository,
)
from src.blacklight.features.agents.spec_schema import AgentSpec
from src.blacklight.features.agents.spec_reviser import SpecReviser, SpecRevisionError
from src.blacklight.features.agents.test_runner import AgentTestRunner, TestExecutionError


class BuildPipelineError(Exception):
    """Raised when build pipeline encounters an error"""

    pass


class BuildPipeline:
    """
    Orchestrates the complete agent build process.

    Flow:
    1. Create version record
    2. Generate code from spec
    3. Validate syntax
    4. Run tests in sandbox
    5. Update status (READY or FAILED)
    """

    def __init__(
        self,
        version_repo: AgentVersionRepository,
        log_repo: AgentBuildLogRepository,
        test_run_repo: AgentTestRunRepository,
        agent_repo: AgentRepository,
        sandbox_root: Path,
        error_analyzer: ErrorAnalyzer | None = None,
        spec_reviser: SpecReviser | None = None,
        max_retries: int = 3,
    ):
        """
        Initialize build pipeline.

        Args:
            version_repo: Repository for agent versions
            log_repo: Repository for build logs
            test_run_repo: Repository for test runs
            agent_repo: Repository for agents
            sandbox_root: Root directory for generated code
            error_analyzer: Service for analyzing build failures (optional)
            spec_reviser: Service for revising failed specs (optional)
            max_retries: Maximum retry attempts for failed builds
        """
        self.version_repo = version_repo
        self.log_repo = log_repo
        self.test_run_repo = test_run_repo
        self.agent_repo = agent_repo
        self.sandbox_root = sandbox_root
        self.error_analyzer = error_analyzer
        self.spec_reviser = spec_reviser
        self.max_retries = max_retries

        self.code_generator = CodeGenerator()
        self.test_runner = AgentTestRunner()

    async def run(
        self,
        agent_id: str,
        spec: AgentSpec,
    ) -> Any:  # Returns AgentVersion
        """
        Run the complete build pipeline with automatic retry on failure.

        If error_analyzer and spec_reviser are available, will automatically
        retry failed builds with revised specs.

        Args:
            agent_id: Agent ID
            spec: Validated agent specification

        Returns:
            AgentVersion with final status

        Raises:
            BuildPipelineError: If build fails after all retries
        """
        # If self-repair is disabled, run once
        if not self.error_analyzer or not self.spec_reviser:
            return await self._run_single_attempt(agent_id, spec)

        # Run with retry loop
        attempt_history = []
        last_error_category = None
        current_spec = spec

        for attempt in range(1, self.max_retries + 1):
            await self._log(
                None,
                "compile",
                "INFO",
                f"Build attempt {attempt}/{self.max_retries} for agent {agent_id}",
            )

            # Run single build attempt
            version = await self._run_single_attempt(agent_id, current_spec)

            # Success - return immediately
            if version.build_status == BuildStatusEnum.READY:
                await self._log(
                    version.id,
                    "compile",
                    "INFO",
                    f"Build succeeded on attempt {attempt}",
                )
                return version

            # Failed - analyze errors
            await self._log(
                version.id, "compile", "WARN", f"Build attempt {attempt} failed, analyzing errors"
            )

            try:
                error_analysis = self.error_analyzer.analyze_build_failure(version)
                await self._log(
                    version.id,
                    "fixpass",
                    "INFO",
                    f"Error category: {error_analysis.category.value}",
                )

                # Check for repeated errors
                if error_analysis.category == last_error_category and attempt > 1:
                    await self._log(
                        version.id,
                        "fixpass",
                        "ERROR",
                        "Same error repeated - aborting retry loop",
                    )
                    return version

                last_error_category = error_analysis.category

                # Add to history
                attempt_history.append({
                    "attempt": attempt,
                    "error_category": error_analysis.category.value,
                    "error_summary": error_analysis.error_messages[0]
                    if error_analysis.error_messages
                    else "Unknown",
                })

                # Last attempt - don't retry
                if attempt >= self.max_retries:
                    await self._log(
                        version.id, "fixpass", "ERROR", "Max retries reached - build failed"
                    )
                    return version

                # Try quick fix for edge format errors
                if error_analysis.category == ErrorCategory.EDGE_FORMAT:
                    await self._log(
                        version.id, "fixpass", "INFO", "Applying quick fix for edge format"
                    )
                    revised_spec_dict = await self.spec_reviser.quick_fix_edge_format(
                        current_spec.model_dump()
                    )
                else:
                    # Use LLM to revise spec
                    await self._log(version.id, "fixpass", "INFO", "Requesting LLM spec revision")
                    revised_spec_dict = await self.spec_reviser.revise_spec(
                        original_spec=current_spec.model_dump(),
                        error_analysis=error_analysis,
                        attempt_history=attempt_history,
                    )

                # Validate revised spec
                current_spec = AgentSpec(**revised_spec_dict)
                await self._log(
                    version.id, "fixpass", "INFO", f"Spec revised successfully, retrying build"
                )

                # Create version diff record
                await self._create_version_diff(
                    from_version_id=version.id,
                    diff_type="retry_fix",
                    changes={
                        "error_category": error_analysis.category.value,
                        "spec_changes": "Revised spec to fix errors",
                    },
                    reason=f"Fix {error_analysis.category.value} error",
                )

            except SpecRevisionError as e:
                await self._log(version.id, "fixpass", "ERROR", f"Spec revision failed: {e}")
                return version

            except Exception as e:
                await self._log(
                    version.id, "fixpass", "ERROR", f"Unexpected error during revision: {e}"
                )
                return version

        # Should not reach here
        return version

    async def _run_single_attempt(
        self,
        agent_id: str,
        spec: AgentSpec,
    ) -> Any:  # Returns AgentVersion
        """
        Run a single build attempt without retry.

        Args:
            agent_id: Agent ID
            spec: Validated agent specification

        Returns:
            AgentVersion with final status

        Raises:
            BuildPipelineError: If build fails
        """
        version = None
        start_time = datetime.utcnow()

        try:
            # Step 1: Create version record
            await self._log(None, "compile", "INFO", f"Starting build for agent {agent_id}")
            version = await self.version_repo.create_version(
                agent_id=agent_id,
                spec=spec.model_dump(),
            )
            version_id = version.id
            await self._log(version_id, "compile", "INFO", f"Created version {version.version}")

            # Step 2: Generate code
            await self._update_status(version_id, BuildStatusEnum.BUILDING)
            code_path = await self._generate_code(version_id, agent_id, spec, version.version)

            # Step 3: Validate syntax
            is_valid, error_msg = await self._validate_syntax(version_id, code_path)
            if not is_valid:
                await self._handle_failure(
                    version_id, agent_id, "Syntax validation failed", {"error": error_msg}
                )
                return await self.version_repo.get_by_id(version_id)

            # Step 4: Run tests
            await self._update_status(version_id, BuildStatusEnum.TESTING)
            all_passed, report = await self._run_tests(version_id, code_path, spec)

            # Step 5: Update final status
            if all_passed:
                await self._handle_success(version_id, agent_id, code_path, report)
            else:
                await self._handle_failure(
                    version_id,
                    agent_id,
                    "Tests failed",
                    {"test_report": report},
                )

            # Calculate metrics
            total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            metrics = {
                "compile_time_ms": total_duration_ms,
                "test_duration_ms": report.get("summary", {}).get("total_duration_ms", 0),
                "tests": {
                    "total": report.get("total", 0),
                    "passed": report.get("passed", 0),
                    "failed": report.get("failed", 0),
                },
            }
            await self.version_repo.update(version_id, metrics=metrics)

            return await self.version_repo.get_by_id(version_id)

        except Exception as e:
            if version:
                await self._handle_failure(
                    version.id, agent_id, f"Build error: {str(e)}", {"exception": str(e)}
                )
                return await self.version_repo.get_by_id(version.id)
            raise BuildPipelineError(f"Build pipeline failed: {e}") from e

    async def _generate_code(
        self, version_id: str, agent_id: str, spec: AgentSpec, version: int
    ) -> Path:
        """Generate Python code from spec"""
        try:
            await self._log(version_id, "compile", "INFO", "Generating code from specification")

            output_dir = self.sandbox_root / "agents" / agent_id
            code_path = self.code_generator.generate(spec, output_dir, version)

            await self._log(
                version_id, "compile", "INFO", f"Code generated at {code_path}"
            )
            return code_path

        except CodeGenerationError as e:
            await self._log(version_id, "compile", "ERROR", f"Code generation failed: {e}")
            raise

    async def _validate_syntax(self, version_id: str, code_path: Path) -> tuple[bool, str]:
        """Validate generated Python syntax"""
        try:
            await self._log(version_id, "compile", "INFO", "Validating syntax")

            is_valid, message = self.code_generator.validate_syntax(code_path)

            if is_valid:
                await self._log(version_id, "compile", "INFO", "Syntax validation passed")
            else:
                await self._log(version_id, "compile", "ERROR", f"Syntax error: {message}")

            return is_valid, message

        except Exception as e:
            error_msg = f"Syntax validation error: {e}"
            await self._log(version_id, "compile", "ERROR", error_msg)
            return False, error_msg

    async def _run_tests(
        self, version_id: str, code_path: Path, spec: AgentSpec
    ) -> tuple[bool, dict]:
        """Run tests in Docker sandbox"""
        try:
            await self._log(version_id, "test", "INFO", f"Running {len(spec.tests)} test(s)")

            # Create test run record
            test_run = await self.test_run_repo.create_test_run(version_id)
            await self.test_run_repo.update_test_run(test_run.id, "RUNNING")

            # Execute tests
            all_passed, report = await self.test_runner.run(code_path, spec)

            # Update test run with results
            await self.test_run_repo.update_test_run(
                test_run.id,
                status="PASSED" if all_passed else "FAILED",
                report=report,
                completed_at=datetime.utcnow(),
            )

            # Log results
            for test_case in report.get("cases", []):
                status = test_case.get("status", "unknown")
                name = test_case.get("name", "unnamed")
                await self._log(
                    version_id, "test", "INFO" if status == "passed" else "ERROR",
                    f"Test '{name}': {status}"
                )

            return all_passed, report

        except TestExecutionError as e:
            await self._log(version_id, "test", "ERROR", f"Test execution failed: {e}")
            return False, {"error": str(e), "total": 0, "passed": 0, "failed": 0}

    async def _update_status(self, version_id: str, status: BuildStatusEnum):
        """Update version build status"""
        await self.version_repo.update_build_status(version_id, status)

    async def _handle_success(
        self, version_id: str, agent_id: str, code_path: Path, report: dict
    ):
        """Handle successful build"""
        await self._log(version_id, "compile", "INFO", "Build successful - agent is READY")

        # Update version
        await self.version_repo.update_build_status(
            version_id, BuildStatusEnum.READY, code_path=str(code_path)
        )

        # Update agent status
        from src.blacklight.features.agents.models import AgentStatusEnum
        await self.agent_repo.update(agent_id, status=AgentStatusEnum.READY)

    async def _handle_failure(
        self, version_id: str, agent_id: str, reason: str, error_details: dict
    ):
        """Handle build failure"""
        await self._log(version_id, "compile", "ERROR", f"Build failed: {reason}")

        # Update version
        await self.version_repo.update_build_status(
            version_id, BuildStatusEnum.FAILED, error_details=error_details
        )

        # Update agent status
        from src.blacklight.features.agents.models import AgentStatusEnum
        await self.agent_repo.update(agent_id, status=AgentStatusEnum.FAILED)

    async def _log(self, version_id: str | None, stage: str, level: str, message: str):
        """Add log entry"""
        if version_id:
            await self.log_repo.add_log(
                agent_version_id=version_id,
                stage=stage,
                level=level,
                message=message,
            )

    async def _create_version_diff(
        self,
        from_version_id: str,
        diff_type: str,
        changes: dict,
        reason: str,
        to_version_id: str | None = None,
    ):
        """
        Create a version diff record.

        Args:
            from_version_id: Source version ID
            diff_type: Type of diff (e.g., "retry_fix")
            changes: Changes dictionary
            reason: Reason for the change
            to_version_id: Target version ID (optional, will use next version if not provided)
        """
        import uuid

        from src.blacklight.features.agents.models import AgentVersionDiff

        # If to_version_id not provided, it will be set when next version is created
        # For now, we'll store a placeholder and update later if needed
        diff = AgentVersionDiff(
            id=str(uuid.uuid4()),
            from_version_id=from_version_id,
            to_version_id=to_version_id or from_version_id,  # Temporary
            diff_type=diff_type,
            changes=changes,
            reason=reason,
        )

        # Note: This would normally be saved to database via a repository
        # For now, we'll add this functionality when integrating with the version repository

    async def stream_logs(self, version_id: str) -> AsyncIterator[dict]:
        """
        Stream build logs for a version (for SSE).

        Args:
            version_id: Version ID

        Yields:
            Log entry dictionaries
        """
        # In a real implementation, this would use a pub/sub system
        # or polling to get new logs as they're created
        logs = await self.log_repo.get_logs_by_version(version_id)

        for log in logs:
            yield {
                "stage": log.stage,
                "level": log.level,
                "message": log.message,
                "timestamp": log.created_at.isoformat(),
            }

            # Small delay to simulate streaming
            await asyncio.sleep(0.05)
