"""
Storage module for Skill Dependency Graph.

Provides JSON file-based storage for the skill dependency graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_dependency.schema import SkillGraph


class GraphStorage:
    """Handles persistence of SkillGraph to JSON files."""

    def __init__(self, storage_path: str | Path) -> None:
        """Initialize storage with path to JSON file.

        Args:
            storage_path: Path to the JSON file for storing the graph
        """
        self.storage_path = Path(storage_path)

    def save(self, graph: SkillGraph) -> None:
        """Save graph to JSON file.

        Args:
            graph: SkillGraph to save
        """
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = graph.model_dump()
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> SkillGraph:
        """Load graph from JSON file.

        Returns:
            SkillGraph loaded from file, or empty graph if file doesn't exist
        """
        if not self.storage_path.exists():
            return SkillGraph()

        with open(self.storage_path, encoding="utf-8") as f:
            data = json.load(f)

        return SkillGraph.from_dict(data)

    def exists(self) -> bool:
        """Check if storage file exists."""
        return self.storage_path.exists()

    def delete(self) -> None:
        """Delete the storage file."""
        if self.storage_path.exists():
            self.storage_path.unlink()
