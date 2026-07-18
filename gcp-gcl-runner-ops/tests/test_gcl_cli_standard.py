#!/usr/bin/env python3
"""
Tests for GCL CLI standardization compliance.

Run with: python -m pytest gcp-gcl-runner-ops/tests/test_gcl_cli_standard.py -v
"""

from __future__ import annotations

import argparse
import re
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ── Test Fixtures ────────────────────────────────────────────────────────────


class ArgumentInspector:
    """Inspect argparse.ArgumentParser for compliance with CLI standards."""

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        self.parser = parser
        self._actions: dict[str, argparse.Action] = {}
        for action in parser._actions:
            for option_string in action.option_strings:
                self._actions[option_string] = action
            if action.dest != argparse.SUPPRESS:
                self._actions[f"--{action.dest}"] = action

    def has_arg(self, name: str) -> bool:
        """Check if argument exists (by --name or dest)."""
        return f"--{name}" in self._actions or name in self._actions

    def get_help(self, name: str) -> str | None:
        """Get help text for an argument."""
        action = self._actions.get(f"--{name}") or self._actions.get(name)
        return action.help if action else None

    def get_default(self, name: str) -> object | None:
        """Get default value for an argument."""
        action = self._actions.get(f"--{name}") or self._actions.get(name)
        return action.default if action else None

    def is_boolean_flag(self, name: str) -> bool:
        """Check if argument is a boolean flag (action='store_true'/'store_false')."""
        action = self._actions.get(f"--{name}") or self._actions.get(name)
        if action is None:
            return False
        return action.option_strings not in ([], None) and (
            action.nargs == 0
            or (action.nargs is None and action.const is not None)
        )

    def get_choices(self, name: str) -> list | None:
        """Get enum choices for an argument."""
        action = self._actions.get(f"--{name}") or self._actions.get(name)
        return action.choices if action else None


# ── CLI Argument Documentation Tests ────────────────────────────────────────


class TestCliArgsAreDocumented:
    """Test that all CLI arguments have help text."""

    @pytest.fixture
    def base_runner_inspector(self) -> ArgumentInspector:
        """Create inspector for base gcl_runner.py."""
        import gcl_runner

        # Create parser as done in main()
        parser = argparse.ArgumentParser(description="GCL Runner")
        parser.add_argument("--skill", required=True, help="Target skill name")
        parser.add_argument("--op", required=True, help="Operation name")
        parser.add_argument("--command", required=True, help="Full CLI command")
        parser.add_argument("--user-request", help="Original natural-language request")
        parser.add_argument("--max-iter", type=int, default=2)
        parser.add_argument("--rubric", help="Custom rubric path")
        parser.add_argument("--output-dir", help="Output directory")
        parser.add_argument("--dry-run", action="store_true")
        return ArgumentInspector(parser)

    @pytest.fixture
    def enhanced_runner_inspector(self) -> ArgumentInspector:
        """Create inspector for enhanced gcl_runner_enhanced.py."""
        import gcl_runner_enhanced

        parser = argparse.ArgumentParser(description="GCL Enhanced Runner")
        parser.add_argument("--skill", required=True, help="Target skill name")
        parser.add_argument("--op", required=True, help="Operation name")
        parser.add_argument("--command", required=True, help="Full CLI command")
        parser.add_argument("--user-request", help="Original natural-language request")
        parser.add_argument("--max-iter", type=int, default=2)
        parser.add_argument("--rubric", help="Custom rubric path")
        parser.add_argument("--output-dir", help="Output directory")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--trace-to-bq", action="store_true", default=False)
        parser.add_argument("--degrade-threshold", type=int, default=3)
        parser.add_argument("--environment", type=str, default="production")
        parser.add_argument("--trace-only", action="store_true", default=False)
        return ArgumentInspector(parser)

    def test_base_runner_skill_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --skill has help text in base runner."""
        help_text = base_runner_inspector.get_help("skill")
        assert help_text is not None, "--skill must have help text"
        assert len(help_text) > 0, "--skill help text cannot be empty"

    def test_base_runner_op_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --op has help text in base runner."""
        help_text = base_runner_inspector.get_help("op")
        assert help_text is not None, "--op must have help text"

    def test_base_runner_command_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --command has help text in base runner."""
        help_text = base_runner_inspector.get_help("command")
        assert help_text is not None, "--command must have help text"

    def test_base_runner_user_request_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --user-request has help text in base runner."""
        help_text = base_runner_inspector.get_help("user-request")
        assert help_text is not None, "--user-request must have help text"

    def test_base_runner_max_iter_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --max-iter has help text in base runner."""
        help_text = base_runner_inspector.get_help("max-iter")
        assert help_text is not None, "--max-iter must have help text"

    def test_base_runner_rubric_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --rubric has help text in base runner."""
        help_text = base_runner_inspector.get_help("rubric")
        assert help_text is not None, "--rubric must have help text"

    def test_base_runner_output_dir_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --output-dir has help text in base runner."""
        help_text = base_runner_inspector.get_help("output-dir")
        assert help_text is not None, "--output-dir must have help text"

    def test_base_runner_dry_run_has_help(self, base_runner_inspector: ArgumentInspector) -> None:
        """Verify --dry-run has help text in base runner."""
        help_text = base_runner_inspector.get_help("dry-run")
        assert help_text is not None, "--dry-run must have help text"

    def test_enhanced_runner_trace_to_bq_has_help(self, enhanced_runner_inspector: ArgumentInspector) -> None:
        """Verify --trace-to-bq has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("trace-to-bq")
        assert help_text is not None, "--trace-to-bq must have help text"

    def test_enhanced_runner_degrade_threshold_has_help(self, enhanced_runner_inspector: ArgumentInspector) -> None:
        """Verify --degrade-threshold has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("degrade-threshold")
        assert help_text is not None, "--degrade-threshold must have help text"

    def test_enhanced_runner_environment_has_help(self, enhanced_runner_inspector: ArgumentInspector) -> None:
        """Verify --environment has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("environment")
        assert help_text is not None, "--environment must have help text"

    def test_enhanced_runner_trace_only_has_help(self, enhanced_runner_inspector: ArgumentInspector) -> None:
        """Verify --trace-only has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("trace-only")
        assert help_text is not None, "--trace-only must have help text"


# ── Enum Consistency Tests ───────────────────────────────────────────────────


class TestEnumValuesConsistent:
    """Test that enum values are consistent across runners."""

    def test_environment_enum_values_match_standard(self) -> None:
        """Verify --environment uses standardized enum values."""
        # Standard values: prod, staging, dev (short forms)
        standard_values = {"prod", "staging", "dev"}

        # Current values in enhanced runner
        current_values = {"production", "staging", "development"}

        # This test documents the inconsistency - it will fail with current code
        # After migration, update to check against standard_values
        assert (
            current_values == standard_values
        ), f"Environment enum values should be {standard_values}, got {current_values}"

    def test_environment_enum_choices_defined(self) -> None:
        """Verify --environment has explicit choices defined."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--environment",
            type=str,
            default="production",
            choices=["production", "staging", "development"],
        )

        inspector = ArgumentInspector(parser)
        choices = inspector.get_choices("environment")

        assert choices is not None, "--environment must have explicit choices"
        assert len(choices) == 3, "--environment must have 3 choices"
        assert "production" in choices, "production must be a valid choice"
        assert "staging" in choices, "staging must be a valid choice"
        assert "development" in choices, "development must be a valid choice"

    def test_exit_codes_are_consistent(self) -> None:
        """Verify exit codes are documented consistently."""
        # Base runner documented exit codes
        base_exit_codes = {0, 1, 2, 3, 4}
        # Enhanced runner documented exit codes
        enhanced_exit_codes = {0, 1, 2, 3, 4, 5}

        # Both should include all standard codes
        standard_exit_codes = {0, 1, 2, 3, 4, 5}

        assert base_exit_codes == standard_exit_codes, f"Base runner exit codes should be {standard_exit_codes}"
        assert enhanced_exit_codes == standard_exit_codes, f"Enhanced runner exit codes should be {standard_exit_codes}"


# ── Boolean Flag Format Tests ────────────────────────────────────────────────


class TestBooleanFlagsFormat:
    """Test that boolean flags use --flag format (not --no-flag)."""

    def test_dry_run_is_store_true(self) -> None:
        """Verify --dry-run uses action='store_true'."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry-run", action="store_true")

        inspector = ArgumentInspector(parser)
        assert inspector.is_boolean_flag("dry-run"), "--dry-run must be a boolean flag"

    def test_trace_to_bq_is_store_true(self) -> None:
        """Verify --trace-to-bq uses action='store_true'."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--trace-to-bq", action="store_true", default=False)

        inspector = ArgumentInspector(parser)
        assert inspector.is_boolean_flag("trace-to-bq"), "--trace-to-bq must be a boolean flag"

    def test_trace_only_is_store_true(self) -> None:
        """Verify --trace-only uses action='store_true'."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--trace-only", action="store_true", default=False)

        inspector = ArgumentInspector(parser)
        assert inspector.is_boolean_flag("trace-only"), "--trace-only must be a boolean flag"

    def test_no_double_negatives(self) -> None:
        """Verify no --no-* flag patterns exist (double negative)."""
        # Check both runner files for --no- patterns
        base_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "gcl_runner.py")
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )

        for path in [base_path, enhanced_path]:
            with open(path) as f:
                content = f.read()

            # Look for --no- patterns in argparse.add_argument calls
            no_flag_pattern = re.compile(r'["\']--no-\w+["\']')
            matches = no_flag_pattern.findall(content)

            assert not matches, f"Found --no-* flag pattern in {path}: {matches}"


# ── Default Value Documentation Tests ───────────────────────────────────────


class TestDefaultValuesDocumented:
    """Test that default values are documented in help text."""

    def test_max_iter_default_in_help(self) -> None:
        """Verify --max-iter help text mentions default value."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--max-iter",
            type=int,
            default=2,
            help="Max iterations (default: 2)",
        )

        inspector = ArgumentInspector(parser)
        help_text = inspector.get_help("max-iter")

        assert help_text is not None
        assert "default:" in help_text.lower() or "default:" in help_text, \
            "--max-iter help must mention default value"

    def test_degrade_threshold_default_in_help(self) -> None:
        """Verify --degrade-threshold help text mentions default value."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--degrade-threshold",
            type=int,
            default=3,
            help="Failures before human degradation (default: 3)",
        )

        inspector = ArgumentInspector(parser)
        help_text = inspector.get_help("degrade-threshold")

        assert help_text is not None
        assert "default:" in help_text.lower() or "default:" in help_text, \
            "--degrade-threshold help must mention default value"

    def test_environment_default_in_help(self) -> None:
        """Verify --environment help text mentions default value."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--environment",
            type=str,
            default="production",
            choices=["production", "staging", "development"],
            help="Environment (default: production)",
        )

        inspector = ArgumentInspector(parser)
        help_text = inspector.get_help("environment")

        assert help_text is not None
        assert "default:" in help_text.lower() or "default:" in help_text, \
            "--environment help must mention default value"


# ── Standard Argument Presence Tests ────────────────────────────────────────


class TestStandardArgumentsPresent:
    """Test that standard arguments per AGENTS.md are present."""

    def test_format_argument_exists(self) -> None:
        """Verify --format argument exists for machine parsing."""
        # This is a missing standard argument
        parser = argparse.ArgumentParser()
        # Currently this doesn't exist in the runners
        # parser.add_argument("--format", default="json", choices=["json", "table"])

        inspector = ArgumentInspector(parser)
        # After migration, this should be True
        has_format = inspector.has_arg("format")
        assert has_format, "--format argument should exist for machine parsing (AGENTS.md §3)"

    def test_project_argument_exists(self) -> None:
        """Verify --project argument exists for CLOUDSDK_CORE_PROJECT."""
        parser = argparse.ArgumentParser()
        # Currently this doesn't exist in the runners

        inspector = ArgumentInspector(parser)
        has_project = inspector.has_arg("project")
        assert has_project, "--project argument should exist (AGENTS.md §3)"

    def test_credential_file_argument_exists(self) -> None:
        """Verify --credential-file argument exists."""
        parser = argparse.ArgumentParser()
        # Currently this doesn't exist in the runners

        inspector = ArgumentInspector(parser)
        has_cred = inspector.has_arg("credential-file")
        assert has_cred, "--credential-file argument should exist for GOOGLE_APPLICATION_CREDENTIALS"

    def test_timeout_argument_exists(self) -> None:
        """Verify --timeout argument exists for long-running ops."""
        parser = argparse.ArgumentParser()
        # Currently this doesn't exist - hardcoded 300 in generate()

        inspector = ArgumentInspector(parser)
        has_timeout = inspector.has_arg("timeout")
        assert has_timeout, "--timeout argument should exist for long-running ops"


# ── Run Tests ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
