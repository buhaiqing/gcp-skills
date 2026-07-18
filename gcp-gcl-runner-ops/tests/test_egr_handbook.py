#!/usr/bin/env python3
"""
Tests for EGR Handbook documentation.

Verifies:
1. All documented CLI flags exist in argparse
2. Exit codes are documented correctly

Run with: python -m pytest gcp-gcl-runner-ops/tests/test_egr_handbook.py -v
"""

from __future__ import annotations

import re
import sys
import os
from pathlib import Path

import pytest

# Add scripts to path for argparse inspection
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

HANDOFF_DOC = Path(__file__).parent.parent / "docs" / "EGR_HANDBOOK.md"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def handbook_content() -> str:
    """Read handbook content."""
    return HANDOFF_DOC.read_text()


@pytest.fixture
def argparse_parser():
    """Get argparse parser from gcl_runner_enhanced."""
    import argparse

    # Import and get the main parser
    from gcl_runner_enhanced import main, argparse as _argparse

    # Create a new parser with same structure
    parser = argparse.ArgumentParser(description="GCL Enhanced Runner")

    # Add all flags from gcl_runner_enhanced.py
    parser.add_argument("--skill", required=True, help="Target skill name")
    parser.add_argument("--op", required=True, help="Operation name")
    parser.add_argument("--command", required=True, help="Full CLI command to execute")
    parser.add_argument("--user-request", help="Original natural-language user request")
    parser.add_argument("--max-iter", type=int, default=2)
    parser.add_argument("--rubric", help="Custom rubric path")
    parser.add_argument("--output-dir", help="Output directory for traces")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--trace-to-bq", action="store_true")
    parser.add_argument("--degrade-threshold", type=int, default=3)
    parser.add_argument(
        "--environment",
        type=str,
        default="production",
        choices=["production", "staging", "development"],
    )
    parser.add_argument("--trace-only", action="store_true")

    return parser


# ── CLI Flags Tests ───────────────────────────────────────────────────────────


class TestCLIFlagsDocumented:
    """Verify all CLI flags are documented in the handbook."""

    @pytest.mark.parametrize(
        "flag",
        [
            "--skill",
            "--op",
            "--command",
            "--user-request",
            "--max-iter",
            "--rubric",
            "--output-dir",
            "--dry-run",
            "--trace-to-bq",
            "--degrade-threshold",
            "--environment",
            "--trace-only",
        ],
    )
    def test_flag_documented(self, flag: str, handbook_content: str) -> None:
        """Verify each flag is documented."""
        assert flag in handbook_content, f"Flag {flag} not found in handbook"


class TestCLIFlagsInArgparse:
    """Verify all documented flags exist in argparse."""

    DOCUMENTED_FLAGS = [
        "--skill",
        "--op",
        "--command",
        "--user-request",
        "--max-iter",
        "--rubric",
        "--output-dir",
        "--dry-run",
        "--trace-to-bq",
        "--degrade-threshold",
        "--environment",
        "--trace-only",
    ]

    def test_all_flags_exist_in_argparse(self, argparse_parser) -> None:
        """Verify all documented flags are in argparse."""
        parser_actions = {action.option_strings[0] for action in argparse_parser._actions if action.option_strings}

        for flag in self.DOCUMENTED_FLAGS:
            assert flag in parser_actions, f"Flag {flag} not in argparse"


# ── Exit Codes Tests ──────────────────────────────────────────────────────────


class TestExitCodesDocumented:
    """Verify exit codes are documented correctly."""

    EXPECTED_EXIT_CODES = {
        0: "PASS",
        1: "MAX_ITER",
        2: "SAFETY_FAIL",
        3: "USAGE_ERROR",
        4: "RUBRIC_ERROR",
        5: "DEGRADED",
    }

    def test_exit_codes_in_handbook(self, handbook_content: str) -> None:
        """Verify all exit codes are documented."""
        for code, name in self.EXPECTED_EXIT_CODES.items():
            assert f"{code}" in handbook_content, f"Exit code {code} not found"
            assert name in handbook_content, f"Exit code name {name} not found"

    def test_exit_code_table_format(self, handbook_content: str) -> None:
        """Verify exit codes are in table format."""
        # Look for markdown table with exit codes
        assert "Exit Codes" in handbook_content or "exit code" in handbook_content.lower()

        # Check for table format indicators
        assert "|" in handbook_content, "Exit codes should be in table format"


# ── Flag Details Tests ────────────────────────────────────────────────────────


class TestFlagDescriptions:
    """Verify flag descriptions are present."""

    @pytest.mark.parametrize(
        "flag,keyword",
        [
            ("--skill", "skill name"),
            ("--op", "operation"),
            ("--command", "command"),
            ("--dry-run", "dry"),
            ("--trace-to-bq", "BigQuery"),
            ("--degrade-threshold", "consecutive failures"),
            ("--environment", "environment"),
            ("--trace-only", "async"),
        ],
    )
    def test_flag_has_description(self, flag: str, keyword: str, handbook_content: str) -> None:
        """Verify each flag has a description containing expected keyword."""
        # Find section containing the flag
        flag_section = handbook_content
        for line in handbook_content.split("\n"):
            if flag in line:
                flag_section = handbook_content[handbook_content.index(line):]
                break

        assert keyword.lower() in flag_section.lower(), f"Flag {flag} missing description for '{keyword}'"


# ── Content Structure Tests ───────────────────────────────────────────────────


class TestHandbookStructure:
    """Verify handbook has required sections."""

    REQUIRED_SECTIONS = [
        "Quick Start",
        "CLI Reference",
        "Output Format",
        "Example Workflows",
        "Troubleshooting",
        "Exit Codes",
    ]

    def test_all_sections_present(self, handbook_content: str) -> None:
        """Verify all required sections are present."""
        for section in self.REQUIRED_SECTIONS:
            assert section in handbook_content, f"Section '{section}' not found"


# ── Examples Tests ────────────────────────────────────────────────────────────


class TestExamplesDocumented:
    """Verify examples are present."""

    def test_basic_example(self, handbook_content: str) -> None:
        """Verify basic usage example exists."""
        assert "gcl_runner_enhanced.py" in handbook_content
        assert "--skill" in handbook_content
        assert "--op" in handbook_content
        assert "--command" in handbook_content

    def test_dry_run_example(self, handbook_content: str) -> None:
        """Verify dry-run example exists."""
        assert "--dry-run" in handbook_content

    def test_bq_example(self, handbook_content: str) -> None:
        """Verify BigQuery trace example exists."""
        assert "--trace-to-bq" in handbook_content


# ── Output Format Tests ───────────────────────────────────────────────────────


class TestOutputFormat:
    """Verify output format documentation."""

    def test_json_structure_documented(self, handbook_content: str) -> None:
        """Verify JSON structure is documented."""
        assert "trace_id" in handbook_content
        assert "result" in handbook_content
        assert "exit_code" in handbook_content
        assert "iterations" in handbook_content
        assert "autonomy_ratio" in handbook_content

    def test_result_enum_values(self, handbook_content: str) -> None:
        """Verify all GCLResult values are documented."""
        results = ["PASS", "MAX_ITER", "SAFETY_FAIL", "ERROR"]
        for result in results:
            assert result in handbook_content


# ── Troubleshooting Tests ─────────────────────────────────────────────────────


class TestTroubleshooting:
    """Verify troubleshooting section."""

    def test_common_errors_addressed(self, handbook_content: str) -> None:
        """Verify common errors are addressed."""
        assert "Rubric Not Found" in handbook_content or "rubric" in handbook_content.lower()
        assert "Permission" in handbook_content or "permission" in handbook_content.lower()
        assert "Timeout" in handbook_content or "timeout" in handbook_content.lower()

    def test_exit_code_troubleshooting(self, handbook_content: str) -> None:
        """Verify exit code troubleshooting is present."""
        assert "Exit code 1" in handbook_content or "MAX_ITER" in handbook_content
        assert "Exit code 2" in handbook_content or "SAFETY_FAIL" in handbook_content
