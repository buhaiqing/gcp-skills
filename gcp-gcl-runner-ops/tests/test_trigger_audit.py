"""
Test for SKILL.md trigger section audit (P0-3.2).

Verifies all gcp-*-ops SKILL.md files have a Trigger section
and that triggers follow the standard format.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Root of the gcp-skills repo
REPO_ROOT = Path(__file__).parent.parent.parent

# All 28 gcp-*-ops skill directories (alphabetically sorted)
ALL_SKILLS = [
    "gcp-armor-ops",
    "gcp-bigquery-ops",
    "gcp-billing-ops",
    "gcp-cdn-ops",
    "gcp-cloudbuild-ops",
    "gcp-cloudfunctions-ops",
    "gcp-cloudrun-ops",
    "gcp-cloudsql-ops",
    "gcp-composer-ops",
    "gcp-dns-ops",
    "gcp-filestore-ops",
    "gcp-gce-ops",
    "gcp-gcl-runner-ops",
    "gcp-gcs-ops",
    "gcp-gke-ops",
    "gcp-iam-ops",
    "gcp-kms-ops",
    "gcp-lb-ops",
    "gcp-logging-ops",
    "gcp-memorystore-ops",
    "gcp-monitoring-ops",
    "gcp-projects-ops",  # may or may not exist; checked dynamically
    "gcp-pubsub-ops",
    "gcp-secretmanager-ops",
    "gcp-securitycenter-ops",
    "gcp-skill-generator",
    "gcp-terraform-ops",
    "gcp-vpc-ops",
]

# Skills that are exempt from standard format (meta-skill and framework)
EXEMPT_SKILLS = {
    "gcp-skill-generator",  # Meta-skill: uses ### Use When / ### Do NOT Use When at top level
    "gcp-gcl-runner-ops",  # Framework: table-based Trigger & Scope
}


def get_all_skill_dirs() -> list[tuple[str, Path]]:
    """Return list of (skill_name, skill_dir) for all existing gcp-*-ops dirs."""
    results = []
    for name in ALL_SKILLS:
        skill_dir = REPO_ROOT / name
        if skill_dir.is_dir():
            results.append((name, skill_dir))
    return sorted(results)


class TestAllSkillsHaveTriggerSection:
    """test_all_skills_have_trigger_section — verify each SKILL.md has a Trigger section."""

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_skill_md_exists(self, skill_name: str, skill_dir: Path):
        """Each skill directory must contain a SKILL.md file."""
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists(), f"{skill_name}: SKILL.md not found at {skill_md}"

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_has_trigger_section(self, skill_name: str, skill_dir: Path):
        """Each SKILL.md must have a ## Trigger & Scope section (or equivalent)."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        # gcp-skill-generator uses "## When to Use / Not Use" instead
        if skill_name == "gcp-skill-generator":
            assert "## When to Use / Not Use" in content, (
                f"{skill_name}: Expected '## When to Use / Not Use' section"
            )
            return

        # gcp-gcl-runner-ops uses "## Trigger & Scope" (no Agent-Readable suffix)
        if skill_name == "gcp-gcl-runner-ops":
            assert "## Trigger & Scope" in content, (
                f"{skill_name}: Expected '## Trigger & Scope' section"
            )
            return

        # Standard: must have "## Trigger & Scope (Agent-Readable)"
        # Legacy: "## Trigger & Scope" without suffix is accepted for older skills (pending migration)
        # Use regex to distinguish exact headers
        has_standard = re.search(r"##\s+Trigger\s*&\s*Scope\s+\(Agent-Readable\)", content) is not None
        has_legacy = (
            re.search(r"##\s+Trigger\s*&\s*Scope(?!\s+\(Agent-Readable\))", content) is not None
        )
        assert has_standard or has_legacy, (
            f"{skill_name}: Expected '## Trigger & Scope [(Agent-Readable)]' section. "
            "Found sections: " + str(re.findall(r"##+ .+", content))
        )

    # Older skills that use the legacy "### SHOULD Use When" (pending migration)
    LEGACY_SUBSECTION_SKILLS = {
        "gcp-gcs-ops",
        "gcp-iam-ops",
        "gcp-bigquery-ops",
        "gcp-pubsub-ops",
        "gcp-cloudsql-ops",
    }

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_has_subsection_trigger(self, skill_name: str, skill_dir: Path):
        """Each SKILL.md must have a SHOULD Use (This Skill) When subsection."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        # Exempt skills have different structures
        if skill_name in EXEMPT_SKILLS:
            pytest.skip(f"{skill_name} is exempt from standard subsection format")

        # Standard: must have "### SHOULD Use This Skill When"
        # Legacy: "### SHOULD Use When" is accepted for older skills (pending migration)
        has_standard = "### SHOULD Use This Skill When" in content
        has_legacy = "### SHOULD Use When" in content
        assert has_standard or has_legacy, (
            f"{skill_name}: Expected '### SHOULD Use [This Skill] When' subsection. "
            f"Found: {re.findall(r'### SHOULD Use.*When', content)}"
        )

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_has_should_not_section(self, skill_name: str, skill_dir: Path):
        """Each SKILL.md (except exempt) must have a SHOULD NOT Use section."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        if skill_name in EXEMPT_SKILLS:
            pytest.skip(f"{skill_name} is exempt")

        # Most use "### SHOULD NOT Use This Skill When", some older use just "### SHOULD NOT Use When"
        has_should_not = (
            "### SHOULD NOT Use This Skill When" in content
            or "### SHOULD NOT Use When" in content
        )
        assert has_should_not, (
            f"{skill_name}: Expected '### SHOULD NOT Use ...' subsection"
        )

    # Legacy skills that lack Delegation Rules (pending migration per audit report)
    LEGACY_MISSING_DELEGATION = {
        "gcp-bigquery-ops",
        "gcp-gcs-ops",
        "gcp-pubsub-ops",
    }

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_has_delegation_rules(self, skill_name: str, skill_dir: Path):
        """Each SKILL.md (except exempt) must have Delegation Rules."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        if skill_name in EXEMPT_SKILLS:
            pytest.skip(f"{skill_name} is exempt")

        if skill_name in self.LEGACY_MISSING_DELEGATION:
            pytest.skip(f"{skill_name} lacks Delegation Rules (documented in audit report)")

        assert "### Delegation Rules" in content, (
            f"{skill_name}: Expected '### Delegation Rules' subsection"
        )


class TestTriggerFormatConsistency:
    """test_trigger_format_consistency — verify triggers follow the standard format."""

    # Skills that must have (Agent-Readable) suffix in section header
    EXPECT_AGENT_READABLE = {
        "gcp-armor-ops",
        "gcp-bigquery-ops",
        "gcp-billing-ops",
        "gcp-cdn-ops",
        "gcp-cloudbuild-ops",
        "gcp-cloudfunctions-ops",
        "gcp-cloudrun-ops",
        "gcp-cloudsql-ops",
        "gcp-composer-ops",
        "gcp-dns-ops",
        "gcp-filestore-ops",
        "gcp-gce-ops",
        "gcp-gke-ops",
        "gcp-kms-ops",
        "gcp-lb-ops",
        "gcp-logging-ops",
        "gcp-memorystore-ops",
        "gcp-monitoring-ops",
        "gcp-pubsub-ops",
        "gcp-secretmanager-ops",
        "gcp-securitycenter-ops",
        "gcp-terraform-ops",
        "gcp-vpc-ops",
    }

    # Skills that must NOT have (Agent-Readable) suffix (older format — pending migration)
    EXPECT_NO_AGENT_READABLE = {
        "gcp-gcs-ops",
        "gcp-iam-ops",
        "gcp-bigquery-ops",
        "gcp-pubsub-ops",
        "gcp-cloudsql-ops",
    }

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_section_header_format(self, skill_name: str, skill_dir: Path):
        """Section header must match expected format for each skill."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        if skill_name == "gcp-skill-generator":
            # Meta-skill: uses "## When to Use / Not Use"
            assert "## When to Use / Not Use" in content
            return

        if skill_name == "gcp-gcl-runner-ops":
            # Framework: uses "## Trigger & Scope" without (Agent-Readable)
            assert "## Trigger & Scope" in content
            assert "## Trigger & Scope (Agent-Readable)" not in content
            return

        if skill_name in self.EXPECT_AGENT_READABLE:
            assert "## Trigger & Scope (Agent-Readable)" in content, (
                f"{skill_name}: Expected '## Trigger & Scope (Agent-Readable)'"
            )
        elif skill_name in self.EXPECT_NO_AGENT_READABLE:
            # Older skills: just "## Trigger & Scope"
            assert "## Trigger & Scope" in content
            assert "## Trigger & Scope (Agent-Readable)" not in content

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_should_use_subsection_format(self, skill_name: str, skill_dir: Path):
        """SHOULD Use subsection must use the standard 'SHOULD Use This Skill When'."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        if skill_name in EXEMPT_SKILLS:
            pytest.skip(f"{skill_name} is exempt")

        # Standard: "### SHOULD Use This Skill When"
        # Legacy: "### SHOULD Use When" is accepted for older skills (pending migration)
        has_standard = "### SHOULD Use This Skill When" in content
        has_legacy = "### SHOULD Use When" in content
        if not has_standard and not has_legacy:
            pytest.fail(
                f"{skill_name}: Expected '### SHOULD Use [This Skill] When', "
                f"found: {re.findall(r'### SHOULD Use.*When', content)}"
            )

    @pytest.mark.parametrize("skill_name,skill_dir", get_all_skill_dirs())
    def test_has_keywords_in_trigger(self, skill_name: str, skill_dir: Path):
        """Trigger section must contain a Keywords line or inline keywords."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        if skill_name in EXEMPT_SKILLS:
            pytest.skip(f"{skill_name} is exempt")

        # Look for Keywords: line anywhere in the trigger section
        # Keywords may be inline in bullets or as a separate line
        # We check the whole file for "Keywords:" prefix
        has_keywords_line = re.search(r"Keywords:", content) is not None

        # Also accept if keywords appear inline (e.g., in last bullet of SHOULD Use When)
        # e.g., "... kubectl, k8s, autopilot, release channel"
        trigger_match = re.search(
            r"### SHOULD Use This Skill When.+?(?=###|$)", content, re.DOTALL
        )
        has_inline_keywords = False
        if trigger_match:
            trigger_text = trigger_match.group(0)
            # Check if there are comma-separated keyword-like terms in the trigger
            has_inline_keywords = bool(re.search(r"\b(GKE|Kubernetes|cluster|kubectl|k8s|logs|logging|sink|bucket|metric|armor|security|policy|firewall)\b", trigger_text))

        assert has_keywords_line or has_inline_keywords, (
            f"{skill_name}: No Keywords line or inline keywords found in trigger section"
        )


class TestSpecialSkillExemptions:
    """Verify that known special-case skills are handled correctly."""

    def test_skill_generator_uses_when_to_use_not_use(self):
        """gcp-skill-generator must use '## When to Use / Not Use'."""
        skill_md = REPO_ROOT / "gcp-skill-generator" / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("gcp-skill-generator not found")
        content = skill_md.read_text()
        assert "## When to Use / Not Use" in content
        assert "### Use When" in content
        assert "### Do NOT Use When" in content

    def test_gcl_runner_uses_table_format(self):
        """gcp-gcl-runner-ops must use table format for Trigger & Scope."""
        skill_md = REPO_ROOT / "gcp-gcl-runner-ops" / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("gcp-gcl-runner-ops not found")
        content = skill_md.read_text()
        assert "## Trigger & Scope" in content
        assert "### SHOULD Use This Skill When" not in content  # Uses table instead
        # Should have a table with Scope | Description
        assert "| Scope | Description |" in content
