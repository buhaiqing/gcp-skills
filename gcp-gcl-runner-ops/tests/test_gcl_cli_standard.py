#!/usr/bin/env python3
"""
Tests for GCL CLI standardization compliance.

Run with: python -m pytest gcp-gcl-runner-ops/tests/test_gcl_cli_standard.py -v

These tests audit the CLI interface of gcl_runner.py and gcl_runner_enhanced.py
against AGENTS.md conventions and document inconsistencies.
"""

from __future__ import annotations

import argparse
import re
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ── Test Fixtures ────────────────────────────────────────────────────────────


class SourceArgumentInspector:
    """Inspect CLI arguments by parsing source code directly."""

    def __init__(self, source_code: str) -> None:
        self.source_code = source_code
        self._args: dict[str, dict] = {}
        self._parse_add_argument_calls()

    def _parse_add_argument_calls(self) -> None:
        """Extract argparse.add_argument calls from source code."""
        # Match patterns like: parser.add_argument("--skill", required=True, help="...")
        # or parser.add_argument('--op', ...)
        # Handle multiline add_argument calls with re.DOTALL
        pattern = r'add_argument\s*\(\s*["\'](--[^"\']+)["\']'

        for m in re.finditer(pattern, self.source_code):
            arg_name = m.group(1).lstrip("-")
            self._args[arg_name] = {"name": m.group(1), "found": True}

        # Extract help text - handle multiline with re.DOTALL
        help_pattern = r'add_argument\s*\(\s*["\'](--[^"\']+)["\'][^)]*?help\s*=\s*[f]?["\']([^"\']*(?:["\'][^"\']*)*?)["\']'
        for m in re.finditer(help_pattern, self.source_code, re.DOTALL):
            arg_name = m.group(1).lstrip("-")
            if arg_name in self._args:
                self._args[arg_name]["help"] = m.group(2).strip()

        # Extract choices for enum args
        choices_pattern = r'add_argument\s*\(\s*["\'](--[^"\']+)["\'][^)]*?choices\s*=\s*\[[^\]]*\]'
        for m in re.finditer(choices_pattern, self.source_code, re.DOTALL):
            arg_name = m.group(1).lstrip("-")
            if arg_name in self._args:
                self._args[arg_name]["has_choices"] = True

        # Extract action='store_true'
        store_true_pattern = r'add_argument\s*\(\s*["\'](--[^"\']+)["\'][^)]*?action\s*=\s*["\']store_true["\']'
        for m in re.finditer(store_true_pattern, self.source_code, re.DOTALL):
            arg_name = m.group(1).lstrip("-")
            if arg_name in self._args:
                self._args[arg_name]["is_boolean"] = True

    def has_arg(self, name: str) -> bool:
        """Check if argument exists."""
        return name in self._args

    def get_help(self, name: str) -> str | None:
        """Get help text for an argument."""
        return self._args.get(name, {}).get("help")

    def has_choices(self, name: str) -> bool:
        """Check if argument has explicit choices."""
        return self._args.get(name, {}).get("has_choices", False)

    def is_boolean_flag(self, name: str) -> bool:
        """Check if argument is a boolean flag."""
        return self._args.get(name, {}).get("is_boolean", False)


# ── CLI Argument Documentation Tests ────────────────────────────────────────


class TestCliArgsAreDocumented:
    """Test that all CLI arguments have help text."""

    @pytest.fixture
    def base_runner_inspector(self) -> SourceArgumentInspector:
        """Create inspector for base gcl_runner.py."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "gcl_runner.py")
        with open(base_path) as f:
            return SourceArgumentInspector(f.read())

    @pytest.fixture
    def enhanced_runner_inspector(self) -> SourceArgumentInspector:
        """Create inspector for enhanced gcl_runner_enhanced.py."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            return SourceArgumentInspector(f.read())

    def test_base_runner_skill_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --skill has help text in base runner."""
        help_text = base_runner_inspector.get_help("skill")
        assert help_text is not None, "--skill must have help text"
        assert len(help_text) > 0, "--skill help text cannot be empty"

    def test_base_runner_op_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --op has help text in base runner."""
        help_text = base_runner_inspector.get_help("op")
        assert help_text is not None, "--op must have help text"

    def test_base_runner_command_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --command has help text in base runner."""
        help_text = base_runner_inspector.get_help("command")
        assert help_text is not None, "--command must have help text"

    def test_base_runner_user_request_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --user-request has help text in base runner."""
        help_text = base_runner_inspector.get_help("user-request")
        assert help_text is not None, "--user-request must have help text"

    def test_base_runner_max_iter_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --max-iter has help text in base runner."""
        help_text = base_runner_inspector.get_help("max-iter")
        assert help_text is not None, "--max-iter must have help text"

    def test_base_runner_rubric_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --rubric has help text in base runner."""
        help_text = base_runner_inspector.get_help("rubric")
        assert help_text is not None, "--rubric must have help text"

    def test_base_runner_output_dir_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --output-dir has help text in base runner."""
        help_text = base_runner_inspector.get_help("output-dir")
        assert help_text is not None, "--output-dir must have help text"

    def test_base_runner_dry_run_has_help(self, base_runner_inspector: SourceArgumentInspector) -> None:
        """Verify --dry-run has help text in base runner."""
        help_text = base_runner_inspector.get_help("dry-run")
        assert help_text is not None, "--dry-run must have help text"

    def test_enhanced_runner_trace_to_bq_has_help(
        self, enhanced_runner_inspector: SourceArgumentInspector
    ) -> None:
        """Verify --trace-to-bq has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("trace-to-bq")
        assert help_text is not None, "--trace-to-bq must have help text"

    def test_enhanced_runner_degrade_threshold_has_help(
        self, enhanced_runner_inspector: SourceArgumentInspector
    ) -> None:
        """Verify --degrade-threshold has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("degrade-threshold")
        assert help_text is not None, "--degrade-threshold must have help text"

    def test_enhanced_runner_environment_has_help(
        self, enhanced_runner_inspector: SourceArgumentInspector
    ) -> None:
        """Verify --environment has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("environment")
        assert help_text is not None, "--environment must have help text"

    def test_enhanced_runner_trace_only_has_help(
        self, enhanced_runner_inspector: SourceArgumentInspector
    ) -> None:
        """Verify --trace-only has help text in enhanced runner."""
        help_text = enhanced_runner_inspector.get_help("trace-only")
        assert help_text is not None, "--trace-only must have help text"


# ── Enum Consistency Tests ───────────────────────────────────────────────────


class TestEnumValuesConsistent:
    """Test that enum values are consistent across runners."""

    def test_environment_enum_values_match_standard(self) -> None:
        """Verify --environment uses standardized enum values."""
        # Standard values per AGENTS.md: prod, staging, dev (short forms)
        standard_values = {"prod", "staging", "dev"}

        # Current values in enhanced runner (migrated to short forms)
        current_values = {"prod", "staging", "dev"}

        assert (
            current_values == standard_values
        ), f"Environment enum values should be {standard_values}, got {current_values}"

    def test_environment_enum_choices_defined(self) -> None:
        """Verify --environment has explicit choices defined."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        # Look for environment choices
        env_pattern = r'--environment.*?choices\s*=\s*\["([^"\']+)["\',\s]+([^"\']+)["\',\s]+([^"\']+)["\']'
        m = re.search(env_pattern, content, re.DOTALL)
        assert m is not None, "--environment must have explicit choices defined"

        choices = {m.group(1), m.group(2), m.group(3)}
        assert "production" in choices or "prod" in choices, "production/prod must be a valid choice"
        assert "staging" in choices, "staging must be a valid choice"
        assert "development" in choices or "dev" in choices, "development/dev must be a valid choice"

    def test_exit_codes_are_consistent(self) -> None:
        """Verify exit codes are documented consistently."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "gcl_runner.py")
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )

        with open(base_path) as f:
            base_content = f.read()
        with open(enhanced_path) as f:
            enhanced_content = f.read()

        # Extract exit codes from docstrings - match format "0 = PASS, 1 = MAX_ITER, ..."
        # Pattern must handle multiline docstrings
        base_exit_pattern = r"Exit codes:\s*\n\s*((?:\d+\s*=\s*\w+\s*,?\s*)+)"
        enhanced_exit_pattern = r"Exit codes:\s*\n\s*((?:\d+\s*=\s*\w+\s*,?\s*)+)"

        base_match = re.search(base_exit_pattern, base_content, re.DOTALL)
        enhanced_match = re.search(enhanced_exit_pattern, enhanced_content, re.DOTALL)

        assert base_match is not None, "Could not find Exit codes in base runner docstring"
        assert enhanced_match is not None, "Could not find Exit codes in enhanced runner docstring"

        # Extract all numbers from the exit code line
        base_codes = set(int(m) for m in re.findall(r"\d+", base_match.group(1)))
        enhanced_codes = set(int(m) for m in re.findall(r"\d+", enhanced_match.group(1)))

        # Base runner: 0-4, Enhanced runner: 0-5
        assert base_codes == {0, 1, 2, 3, 4}, f"Base runner exit codes should be {{0, 1, 2, 3, 4}}, got {base_codes}"
        assert enhanced_codes == {0, 1, 2, 3, 4, 5}, f"Enhanced runner exit codes should be {{0, 1, 2, 3, 4, 5}}, got {enhanced_codes}"

        # Enhanced runner must superset base runner
        assert enhanced_codes.issuperset(base_codes), "Enhanced runner must document all base runner exit codes"


# ── Boolean Flag Format Tests ────────────────────────────────────────────────


class TestBooleanFlagsFormat:
    """Test that boolean flags use --flag format (not --no-flag)."""

    def test_dry_run_is_store_true(self) -> None:
        """Verify --dry-run uses action='store_true'."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        pattern = r'add_argument\s*\(\s*["\']--dry-run["\']\s*,\s*action\s*=\s*["\']store_true["\']'
        assert re.search(pattern, content), "--dry-run must use action='store_true'"

    def test_trace_to_bq_is_store_true(self) -> None:
        """Verify --trace-to-bq uses action='store_true'."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        pattern = r'add_argument\s*\(\s*["\']--trace-to-bq["\']\s*,\s*action\s*=\s*["\']store_true["\']'
        assert re.search(pattern, content), "--trace-to-bq must use action='store_true'"

    def test_trace_only_is_store_true(self) -> None:
        """Verify --trace-only uses action='store_true'."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        pattern = r'add_argument\s*\(\s*["\']--trace-only["\']\s*,\s*action\s*=\s*["\']store_true["\']'
        assert re.search(pattern, content), "--trace-only must use action='store_true'"

    def test_no_double_negatives(self) -> None:
        """Verify no --no-* flag patterns exist (double negative)."""
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


# ── Standard Argument Presence Tests ────────────────────────────────────────


class TestStandardArgumentsPresent:
    """Test that standard arguments per AGENTS.md are present."""

    def test_format_argument_exists(self) -> None:
        """Verify --format argument exists for machine parsing."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        has_format = re.search(r'add_argument\s*\(\s*["\']--format["\']', content)
        assert has_format, "--format argument should exist for machine parsing (AGENTS.md §3)"

    def test_project_argument_exists(self) -> None:
        """Verify --project argument exists for CLOUDSDK_CORE_PROJECT."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        has_project = re.search(r'add_argument\s*\(\s*["\']--project["\']', content)
        assert has_project, "--project argument should exist (AGENTS.md §3)"

    def test_credential_file_argument_exists(self) -> None:
        """Verify --credential-file argument exists."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        has_cred = re.search(r'add_argument\s*\(\s*["\']--credential-file["\']', content)
        assert has_cred, "--credential-file argument should exist for GOOGLE_APPLICATION_CREDENTIALS"

    def test_timeout_argument_exists(self) -> None:
        """Verify --timeout argument exists for long-running ops."""
        enhanced_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "gcl_runner_enhanced.py"
        )
        with open(enhanced_path) as f:
            content = f.read()

        has_timeout = re.search(r'add_argument\s*\(\s*["\']--timeout["\']', content)
        assert has_timeout, "--timeout argument should exist for long-running ops"


# ── Run Tests ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
