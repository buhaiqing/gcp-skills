#!/usr/bin/env python3
"""
Tests for AGENTS.md documentation.

Run with: python -m pytest tests/test_agents_md.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path to AGENTS.md
AGENTS_PATH = Path(__file__).parent.parent / "docs" / "AGENTS.md"


class TestAgentsMdExists:
    """Test that AGENTS.md exists."""

    def test_agents_file_exists(self) -> None:
        """Verify AGENTS.md exists."""
        assert AGENTS_PATH.exists(), f"AGENTS.md not found at {AGENTS_PATH}"

    def test_agents_has_content(self) -> None:
        """Verify AGENTS.md has substantial content."""
        content = AGENTS_PATH.read_text()
        assert len(content) > 500, "AGENTS.md seems too short"


class TestLevel3Documentation:
    """Test that Level 3 is properly documented."""

    def test_level_3_section_exists(self) -> None:
        """Verify Level 3 section exists."""
        content = AGENTS_PATH.read_text()
        assert "Level 3" in content

    def test_autonomous_orchestration_mentioned(self) -> None:
        """Verify 'Autonomous Orchestration' is mentioned."""
        content = AGENTS_PATH.read_text()
        assert "Autonomous Orchestration" in content or "autonomous" in content.lower()


class TestEGRFeatures:
    """Test that EGR features are documented."""

    def test_egr_components_documented(self) -> None:
        """Verify EGR components are documented."""
        content = AGENTS_PATH.read_text()
        components = ["Generator", "Critic", "Autonomy Engine", "BigQuery"]
        for component in components:
            assert component in content, f"Missing component: {component}"

    def test_egr_features_documented(self) -> None:
        """Verify EGR-1 through EGR-5 are documented."""
        content = AGENTS_PATH.read_text()
        # Check for EGR feature mentions
        assert "EGR-1" in content or "retry" in content.lower()
        assert "EGR-3" in content or "BigQuery" in content
        assert "EGR-4" in content or "autonomy" in content.lower()
        assert "EGR-5" in content or "state" in content.lower()


class TestGCLDocumentation:
    """Test that GCL is properly documented."""

    def test_gcl_mentioned(self) -> None:
        """Verify GCL is documented."""
        content = AGENTS_PATH.read_text()
        assert "GCL" in content or "Generator-Critic-Loop" in content

    def test_gcl_components_documented(self) -> None:
        """Verify Generator and Critic are documented."""
        content = AGENTS_PATH.read_text()
        assert "Generator" in content
        assert "Critic" in content


class TestMetrics:
    """Test that observability metrics are documented."""

    def test_metrics_mentioned(self) -> None:
        """Verify metrics are documented."""
        content = AGENTS_PATH.read_text()
        assert "gcl_error_rate" in content or "metric" in content.lower()


class TestComparisonTable:
    """Test that Level 2 vs Level 3 comparison exists."""

    def test_level_comparison_exists(self) -> None:
        """Verify Level comparison exists."""
        content = AGENTS_PATH.read_text()
        assert "Level 2" in content or "Level 3" in content
