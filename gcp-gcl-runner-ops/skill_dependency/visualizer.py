"""
Visualizer module for Skill Dependency Graph.

Generates Mermaid diagram code from SkillGraph.
"""

from __future__ import annotations

from pathlib import Path

from skill_dependency.schema import SkillGraph, EdgeType


class MermaidVisualizer:
    """Generates Mermaid diagrams from SkillGraph."""

    def generate(self, graph: SkillGraph, output_path: str | Path | None = None) -> str:
        """Generate Mermaid diagram code from graph.

        Args:
            graph: SkillGraph to visualize
            output_path: Optional path to save the .mmd file

        Returns:
            Mermaid diagram code as string
        """
        lines = ["graph TD"]

        # Add node declarations with labels
        for name, node in graph.nodes.items():
            label = self._sanitize_label(name)
            lines.append(f'    {self._safe_id(name)}["{label}"]')

        # Add edges
        for edge in graph.edges:
            source_id = self._safe_id(edge.source)
            target_id = self._safe_id(edge.target)

            # Edge style based on type
            if edge.edge_type == EdgeType.DELEGATION:
                lines.append(f"    {source_id} -->|DELEGATION| {target_id}")
            elif edge.edge_type == EdgeType.DEPENDENCY:
                lines.append(f"    {source_id} -.->|DEP| {target_id}")
            else:
                lines.append(f"    {source_id} --> {target_id}")

        mermaid_code = "\n".join(lines)

        # Save to file if path provided
        if output_path:
            Path(output_path).write_text(mermaid_code, encoding="utf-8")

        return mermaid_code

    def _safe_id(self, name: str) -> str:
        """Convert skill name to safe Mermaid node ID."""
        # Replace hyphens with underscores and ensure valid identifier
        return name.replace("-", "_").replace(".", "_")

    def _sanitize_label(self, name: str) -> str:
        """Sanitize label for display in Mermaid."""
        return name.replace("_", "-")
