"""
Dependency Extractor for SKILL.md files.

Extracts skill nodes and dependency edges from SKILL.md content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from skill_dependency.schema import (
    SkillNode,
    SkillEdge,
    SkillGraph,
    EdgeType,
    NodeType,
)


# Patterns for parsing SKILL.md
DELEGATION_TABLE_PATTERN = re.compile(
    r"## Delegation Rules.*?\n\|[^\n]*\|[^\n]*\|[^\n]*\|\n((?:\|[^\n]*\|\n)+)",
    re.DOTALL | re.IGNORECASE,
)

DELEGATION_SKILL_PATTERN = re.compile(
    r"gcp-[a-z0-9]+(?:-ops)?",
    re.IGNORECASE,
)

TRIGGER_SECTION_PATTERN = re.compile(
    r"### SHOULD Use When\s*\n((?:\s*-\s*[^\n]+\n)+)",
    re.DOTALL | re.IGNORECASE,
)

SKILL_NAME_PATTERN = re.compile(
    r"^name:\s*([^\s]+)\s*$",
    re.MULTILINE,
)

SKILL_TYPE_PATTERN = re.compile(
    r"^type:\s*([^\s]+)\s*$",
    re.MULTILINE,
)


class DependencyExtractor:
    """Extracts dependency relationships from SKILL.md content."""

    def extract(self, skill_md: str | Path) -> tuple[dict[str, SkillNode], list[SkillEdge]]:
        """Extract nodes and edges from SKILL.md content or file.

        Args:
            skill_md: Either SKILL.md content string or path to SKILL.md file

        Returns:
            Tuple of (nodes dict, edges list)
        """
        # Check if it's a file path (string doesn't start with --- and exists on disk)
        if isinstance(skill_md, (str, Path)) and not str(skill_md).strip().startswith("---"):
            if Path(skill_md).exists():
                path = Path(skill_md)
                content = path.read_text()
            else:
                content = str(skill_md)
        else:
            content = str(skill_md)

        nodes: dict[str, SkillNode] = {}
        edges: list[SkillEdge] = []

        # Extract skill name
        skill_name = self._extract_skill_name(content)
        if not skill_name:
            return nodes, edges

        # Determine node type
        node_type = self._extract_node_type(content)

        # Extract triggers
        triggers = self._extract_triggers(content)

        # Extract delegations
        delegations = self._extract_delegations(content)

        # Create the main skill node
        nodes[skill_name] = SkillNode(
            name=skill_name,
            node_type=node_type,
            triggers=triggers,
            delegations=delegations,
        )

        # Create delegation edges
        for delegation_target in delegations:
            edges.append(SkillEdge(
                source=skill_name,
                target=delegation_target,
                edge_type=EdgeType.DELEGATION,
                weight=1.0,
            ))

        # Extract dependency edges from "See Also" and "Should NOT Use When" sections
        dependency_skills = self._extract_referenced_skills(content)
        for dep_skill in dependency_skills:
            if dep_skill != skill_name and dep_skill not in delegations:
                edges.append(SkillEdge(
                    source=skill_name,
                    target=dep_skill,
                    edge_type=EdgeType.DEPENDENCY,
                    weight=0.3,
                ))

        return nodes, edges

    def _extract_skill_name(self, content: str) -> str | None:
        """Extract skill name from frontmatter."""
        # Handle multi-line description format
        match = SKILL_NAME_PATTERN.search(content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_node_type(self, content: str) -> NodeType:
        """Determine node type from content."""
        if "shared-framework" in content.lower():
            return NodeType.SHARED_FRAMEWORK
        if "generator" in content.lower() or "meta-skill" in content.lower():
            return NodeType.GENERATOR
        return NodeType.OPS

    def _extract_triggers(self, content: str) -> list[str]:
        """Extract trigger keywords from SHOULD Use When section."""
        triggers: list[str] = []

        match = TRIGGER_SECTION_PATTERN.search(content)
        if match:
            lines = match.group(1).strip().split("\n")
            for line in lines:
                # Parse "- User mentions "X", "Y", "Z"" - find ALL quoted strings
                matches = re.findall(r'"([^"]+)"', line)
                for match in matches:
                    keywords = match
                    triggers.extend([k.strip() for k in keywords.split(",")])

        # Also extract from trigger section without quotes
        should_use_pattern = re.compile(
            r"### SHOULD Use When\s*\n((?:[^\n]+\n)+)",
            re.IGNORECASE,
        )
        match = should_use_pattern.search(content)
        if match:
            lines = match.group(1).strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-"):
                    line = line[1:].strip()
                    # Skip if it's already parsed as quoted
                    if '"' not in line:
                        triggers.append(line.rstrip(",."))

        return list(set(triggers))  # Remove duplicates

    def _extract_delegations(self, content: str) -> list[str]:
        """Extract delegation targets from Delegation Rules table."""
        delegations: list[str] = []

        # Find the delegation rules section
        match = DELEGATION_TABLE_PATTERN.search(content)
        if match:
            table_content = match.group(1)
            # Find all skill references in the entire table section
            skill_refs = DELEGATION_SKILL_PATTERN.findall(table_content)
            delegations.extend(skill_refs)

        # Also check for explicit delegation references in text
        delegation_refs = re.findall(
            r"delegate.*?to\s+`?([gcp-][a-z0-9-]+)`?",
            content,
            re.IGNORECASE,
        )
        delegations.extend(delegation_refs)

        return list(set(delegations))

    def _extract_referenced_skills(self, content: str) -> list[str]:
        """Extract skill references from See Also and other sections."""
        references: list[str] = []

        # Find all skill references (gcp-xxx-ops pattern)
        references = re.findall(r"\[gcp-[a-z0-9-]+\]", content)
        references = [ref[1:-1] for ref in references]  # Remove brackets

        # Also find inline skill references
        inline_refs = re.findall(r"gcp-[a-z0-9]+(?:-ops)?", content)
        references.extend(inline_refs)

        return list(set(references))
