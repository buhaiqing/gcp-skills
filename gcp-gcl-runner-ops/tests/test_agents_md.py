#!/usr/bin/env python3
"""Tests for gcp-gcl-runner-ops/docs/AGENTS.md Level 3 documentation."""

from __future__ import annotations

import os
import re

import pytest

AGENTS_MD_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "AGENTS.md",
)


class TestLevel3SectionExists:
    """Verify Level 3 section exists in AGENTS.md."""

    def test_agents_md_exists(self):
        assert os.path.exists(AGENTS_MD_PATH), f"AGENTS.md not found at {AGENTS_MD_PATH}"

    def test_level3_overview_section(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "Level 3" in content, "Level 3 Overview section not found"
        assert "EGR-1" in content and "EGR-2" in content, "EGR feature references not found"

    def test_has_level3_heading(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        # Match Level 3 section heading (## 1. Level 3 Overview or similar)
        assert re.search(r"##\s+\d+\.\s+Level\s+3", content), "Level 3 section heading not found"


class TestEGRFeaturesDocumented:
    """Verify all EGR features (EGR-1 through EGR-5) are documented."""

    @pytest.mark.parametrize(
        "feature",
        [
            "EGR-1",
            "EGR-2",
            "EGR-3",
            "EGR-4",
            "EGR-5",
        ],
    )
    def test_egr_feature_exists(self, feature: str):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert feature in content, f"{feature} not documented in AGENTS.md"

    def test_egr1_auto_retry_described(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "Auto-Retry" in content or "retry" in content.lower()
        assert "backoff" in content.lower()

    def test_egr2_safety_termination_described(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "Safety=0" in content or "safety" in content.lower()
        assert "termination" in content.lower() or "terminate" in content.lower()

    def test_egr3_bigquery_logging_described(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "BigQuery" in content
        assert "Cloud Logging" in content or "logging" in content.lower()

    def test_egr4_autonomy_engine_described(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "autonomy_ratio" in content
        assert "degrade" in content.lower() or "degradation" in content.lower()

    def test_egr5_state_snapshot_diff_described(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "State Snapshot" in content or "state" in content.lower()
        assert "diff" in content.lower()


class TestEnhancedComponents:
    """Verify Enhanced GCL Runner components are documented."""

    @pytest.mark.parametrize(
        "component",
        [
            "GCL Runner Core",
            "Autonomy Engine",
            "BigQuery Writer",
            "Cloud Logging",
            "State Snapshot Diff",
        ],
    )
    def test_component_exists(self, component: str):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert component in content, f"{component} not documented"


class TestDataFlowDiagram:
    """Verify data flow diagram is present."""

    def test_has_data_flow_diagram(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        # Look for text-based diagram indicators
        assert "┌─" in content or "│" in content or "└─" in content, "ASCII diagram not found"
        assert "Pre-flight" in content or "pre-flight" in content
        assert "Loop" in content or "loop" in content


class TestLevel2VsLevel3:
    """Verify Level 2 vs Level 3 comparison table exists."""

    def test_has_comparison_table(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "Level 2" in content and "Level 3" in content, "Level 2 vs Level 3 comparison not found"
        assert "EGR-1" in content, "EGR features not in comparison"


class TestExitCodes:
    """Verify exit codes are documented."""

    @pytest.mark.parametrize(
        "code,meaning",
        [
            ("0", "PASS"),
            ("1", "MAX_ITER"),
            ("2", "SAFETY_FAIL"),
            ("3", "USAGE_ERROR"),
            ("4", "RUBRIC_ERROR"),
            ("5", "DEGRADED"),
        ],
    )
    def test_exit_code_documented(self, code: str, meaning: str):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert code in content, f"Exit code {code} not documented"
        assert meaning in content, f"Exit code {code} meaning '{meaning}' not documented"


class TestUsageSection:
    """Verify usage section exists."""

    def test_has_usage_example(self):
        with open(AGENTS_MD_PATH) as f:
            content = f.read()
        assert "python3 gcl_runner_enhanced.py" in content
        assert "--trace-to-bq" in content
        assert "--degrade-threshold" in content
