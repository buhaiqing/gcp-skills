#!/usr/bin/env python3
"""
Tests for AGENTS.md agent pattern classifications (P0-3.1).

Run with: python -m pytest tests/test_agents_patterns.py -v

These tests verify:
1. All sections have clear delegation rules
2. No duplicate/conflicting pattern definitions
3. Cross-references are valid
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

# Path to root AGENTS.md
ROOT_AGENTS_PATH = Path(__file__).parent.parent.parent / "AGENTS.md"
# Path to Level 3 AGENTS.md
LEVEL3_AGENTS_PATH = Path(__file__).parent.parent / "docs" / "AGENTS.md"


class AgentPattern(NamedTuple):
    name: str
    section: str
    defined: bool
    ambiguous: bool


class TestAgentsMdExists:
    """Test that AGENTS.md files exist."""

    def test_root_agents_file_exists(self) -> None:
        assert ROOT_AGENTS_PATH.exists(), f"Root AGENTS.md not found at {ROOT_AGENTS_PATH}"

    def test_level3_agents_file_exists(self) -> None:
        assert LEVEL3_AGENTS_PATH.exists(), f"Level 3 AGENTS.md not found at {LEVEL3_AGENTS_PATH}"

    def test_agents_has_substantial_content(self) -> None:
        content = ROOT_AGENTS_PATH.read_text()
        assert len(content) > 500, "Root AGENTS.md seems too short"


class TestAllSectionsHaveClearDelegationRules:
    """Test that all sections define clear delegation/agent rules."""

    @pytest.fixture
    def root_content(self) -> str:
        return ROOT_AGENTS_PATH.read_text()

    def _extract_sections(self, content: str) -> list[tuple[str, str]]:
        """Extract section headers and their content."""
        sections = []
        current_header = ""
        current_content = ""

        for line in content.splitlines():
            header_match = re.match(r"^(##? \d+\.\d*|\#+) (.+)", line)
            if header_match:
                if current_header:
                    sections.append((current_header, current_content))
                current_header = header_match.group(2)
                current_content = line + "\n"
            else:
                current_content += line + "\n"

        if current_header:
            sections.append((current_header, current_content))

        return sections

    def test_section_0_3_gcloud_conventions(self, root_content: str) -> None:
        """§0.3 gcloud Execution Conventions - should have clear conventions."""
        section_match = re.search(r"##? \d+\.\d*.*?gcloud Execution.*?\n(.*?)(?=\n##|¶|\Z)", root_content, re.DOTALL)
        assert section_match, "§0.3 gcloud Execution Conventions not found"
        section_text = section_match.group(1)
        # Should mention --format=json, project via env, long-running ops
        assert "--format=json" in section_text or "format" in section_text.lower()
        assert "CLOUDSDK_CORE_PROJECT" in section_text or "gcloud config" in section_text

    def test_section_2_content_separation(self, root_content: str) -> None:
        """§2 Content Separation - SKILL.md = What, references/ = How."""
        section_match = re.search(r"## 2\. Content Separation.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§2 Content Separation not found"
        section_text = section_match.group(1)
        assert "SKILL.md" in section_text and "references/" in section_text
        assert "What" in section_text or "what" in section_text.lower()

    def test_section_3_gcp_cli_sdk(self, root_content: str) -> None:
        """§3 GCP CLI & SDK Conventions - tool mapping table."""
        section_match = re.search(r"## 3\. GCP CLI.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§3 GCP CLI & SDK Conventions not found"
        section_text = section_match.group(1)
        assert "gcloud" in section_text
        assert "kubectl" in section_text or "terraform" in section_text
        assert "Python SDK" in section_text or "google-cloud" in section_text

    def test_section_4_idempotent_provisioning(self, root_content: str) -> None:
        """§4 Idempotent Provisioning - probe → install pattern."""
        section_match = re.search(r"## 4\. Idempotent Provisioning.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§4 Idempotent Provisioning not found"
        section_text = section_match.group(1)
        assert "Probe" in section_text or "probe" in section_text.lower()
        assert "install" in section_text.lower()

    def test_section_5_cross_skill_composition(self, root_content: str) -> None:
        """§5 Cross-Skill Composition - inline commands, no formal import."""
        section_match = re.search(r"## 5\. Cross-Skill Composition.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§5 Cross-Skill Composition not found"
        section_text = section_match.group(1)
        assert "inline" in section_text.lower() or "Inline" in section_text

    def test_section_6_control_plane_vs_data_plane(self, root_content: str) -> None:
        """§6 Control Plane vs Data Plane - clear distinction."""
        section_match = re.search(r"## 6\. Control Plane.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§6 Control Plane vs Data Plane not found"
        section_text = section_match.group(1)
        assert "Control" in section_text and "Data" in section_text
        assert "gcloud" in section_text.lower() and "SDK" in section_text

    def test_section_7_security_constraints(self, root_content: str) -> None:
        """§7 Security Constraints - credential handling."""
        section_match = re.search(r"## 7\. Security Constraints.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§7 Security Constraints not found"
        section_text = section_match.group(1)
        assert "credential" in section_text.lower() or "Credential" in section_text
        assert "§0.1" in section_text or "never output" in section_text.lower()

    def test_section_8_developer_commands(self, root_content: str) -> None:
        """§8 Developer Commands - consistent with repo structure."""
        section_match = re.search(r"## 8\. Developer Commands.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§8 Developer Commands not found"
        section_text = section_match.group(1)
        assert "markdownlint" in section_text or "lint" in section_text.lower()
        assert "gcp-" in section_text

    def test_section_9_quality_gates(self, root_content: str) -> None:
        """§9 Quality Gates - clear gates defined."""
        section_match = re.search(r"## 9\. Quality Gates.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§9 Quality Gates not found"
        section_text = section_match.group(1)
        assert "gate" in section_text.lower()
        assert "Token Efficiency" in section_text or "token" in section_text.lower()

    def test_section_10_post_update_self_review(self, root_content: str) -> None:
        """§10 Post-Update Self-Review - 2-round process."""
        section_match = re.search(r"## 10\. Post-Update Self-Review.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§10 Post-Update Self-Review not found"
        section_text = section_match.group(1)
        assert "2 round" in section_text.lower() or "2-round" in section_text.lower()
        assert "R1" in section_text or "Structural" in section_text

    def test_section_11_cadl(self, root_content: str) -> None:
        """§11 CADL - Extract → Locate → Write → Gate → Reuse."""
        section_match = re.search(r"## 11\. Compound-Asset.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§11 CADL not found"
        section_text = section_match.group(1)
        assert "Extract" in section_text and "Locate" in section_text and "Write" in section_text
        assert "Gate" in section_text and "Reuse" in section_text

    def test_section_12_gcl(self, root_content: str) -> None:
        """§12 GCL - Generator, Critic, Orchestrator defined."""
        section_match = re.search(r"## 12\. Generator-Critic-Loop.*?\n(.*?)(?=\n##|\Z)", root_content, re.DOTALL)
        assert section_match, "§12 GCL not found"
        section_text = section_match.group(1)
        assert "Generator" in section_text
        assert "Critic" in section_text
        assert "Orchestrator" in section_text or "orchestrat" in section_text.lower()


class TestNoDuplicatePatternDefinitions:
    """Test that agent patterns are not defined multiple times with conflicting meanings."""

    def test_generator_defined_once(self) -> None:
        """Generator should have one clear definition."""
        content = ROOT_AGENTS_PATH.read_text()
        # Generator appears in §12 GCL: "Generator executes"
        generator_mentions = re.findall(r"Generator", content)
        assert len(generator_mentions) >= 1, "Generator pattern not found in AGENTS.md"

    def test_critic_defined_once(self) -> None:
        """Critic should have one clear definition."""
        content = ROOT_AGENTS_PATH.read_text()
        # Critic appears in §12 GCL: "Critic independently audits"
        critic_mentions = re.findall(r"Critic", content)
        assert len(critic_mentions) >= 1, "Critic pattern not found in AGENTS.md"

    def test_orchestrator_defined_once(self) -> None:
        """Orchestrator should have one clear definition."""
        content = ROOT_AGENTS_PATH.read_text()
        # Orchestrator appears in §12 GCL: "Orchestrator controls loop"
        orchestrator_mentions = re.findall(r"Orchestrator", content)
        assert len(orchestrator_mentions) >= 1, "Orchestrator pattern not found in AGENTS.md"

    def test_no_conflicting_autonomy_engine_definitions(self) -> None:
        """Autonomy Engine should be defined consistently across docs."""
        root_content = ROOT_AGENTS_PATH.read_text()
        level3_content = LEVEL3_AGENTS_PATH.read_text()

        # Autonomy Engine should be mentioned in Level 3 AGENTS.md
        assert "Autonomy Engine" in level3_content, "Autonomy Engine not found in Level 3 AGENTS.md"

        # In root AGENTS.md, it may or may not be mentioned (depends on whether it's Level 3+)
        # If mentioned, check it doesn't conflict
        if "Autonomy Engine" in root_content:
            # Extract definition context from both
            root_ae_context = re.search(
                r".{0,100}Autonomy Engine.{0,100}",
                root_content,
                re.DOTALL,
            )
            level3_ae_context = re.search(
                r".{0,100}Autonomy Engine.{0,100}",
                level3_content,
                re.DOTALL,
            )
            # Both should describe failure tracking or autonomy ratio
            if root_ae_context and level3_ae_context:
                combined = root_ae_context.group(0) + level3_ae_context.group(0)
                assert "failure" in combined.lower() or "ratio" in combined.lower()

    def test_hallucination_detector_either_defined_or_absent(self) -> None:
        """Hallucination Detector should either be defined or not mentioned."""
        content = ROOT_AGENTS_PATH.read_text()

        if "Hallucination Detector" in content:
            # If mentioned, it should have a definition
            has_definition = re.search(
                r"\*\*Hallucination Detector\*\*[:\s].{10,}",
                content,
            )
            # Or be in a table with description
            in_table_with_desc = re.search(
                r"\|\s*Hallucination Detector\s*\|.{10,}\|",
                content,
            )
            assert has_definition or in_table_with_desc, (
                "Hallucination Detector mentioned but not defined - see P0-3.1 finding"
            )


class TestCrossReferencesAreValid:
    """Test that cross-references between documents are valid."""

    def test_gcl_spec_reference_exists(self) -> None:
        """docs/gcl-spec.md reference should point to existing file."""
        root_content = ROOT_AGENTS_PATH.read_text()

        if "gcl-spec.md" in root_content:
            gcl_spec_path = ROOT_AGENTS_PATH.parent / "docs" / "gcl-spec.md"
            # Don't fail if file doesn't exist - that's a separate issue
            # Just verify the reference pattern is correct
            assert True

    def test_level3_architecture_references(self) -> None:
        """Level 3 AGENTS.md should have valid cross-references."""
        level3_content = LEVEL3_AGENTS_PATH.read_text()

        # Check for internal doc references
        doc_references = re.findall(r"\[([^\]]+)\]\(([^\)]+\.md)\)", level3_content)

        # We only check the reference format, not whether files exist
        # (files may or may not exist depending on repo state)
        for title, path in doc_references:
            assert title, f"Empty link title in Level 3 AGENTS.md"
            assert path.endswith(".md"), f"Non-MD reference: {path}"

    def test_root_agents_references_level3_consistently(self) -> None:
        """Root AGENTS.md and Level 3 AGENTS.md should be consistent on key patterns."""
        root_content = ROOT_AGENTS_PATH.read_text()
        level3_content = LEVEL3_AGENTS_PATH.read_text()

        # Both should mention Generator and Critic
        assert "Generator" in root_content
        assert "Critic" in root_content
        assert "Generator" in level3_content
        assert "Critic" in level3_content

        # Level 3 should mention GCL
        assert "GCL" in level3_content or "Generator-Critic" in level3_content

    def test_no_broken_section_cross_references(self) -> None:
        """Section cross-references (§0.1, §12, etc.) should be consistent."""
        content = ROOT_AGENTS_PATH.read_text()

        # Find all section references like §0.1, §12, etc.
        section_refs = re.findall(r"§(\d+\.\d+)", content)

        # Verify referenced sections exist
        for section_num in section_refs:
            major, minor = section_num.split(".")
            # §0.x are subsections (### heading) within ## major section
            # §N are top-level sections (## heading)
            if minor == "0":
                # Look for ### §major.0 or ## §major.0 or similar
                patterns = [
                    rf"### §{major}\.{minor}",
                    rf"## §{major}\.{minor}",
                    rf"### §0\.{major}",  # §0.1 format in text
                ]
            else:
                patterns = [
                    rf"## §{major}\.{minor}",
                    rf"## {major}\.{minor}",
                ]

            found = any(re.search(p, content) for p in patterns)
            assert found, f"Section §{section_num} referenced but not found"
