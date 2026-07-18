"""
Schema definitions for Skill Dependency Graph.

Defines the core data structures: SkillNode, SkillEdge, and SkillGraph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Type of skill node."""
    OPS = "ops"                    # Regular GCP ops skill
    SHARED_FRAMEWORK = "shared_framework"  # Shared framework skill (e.g., GCL runner)
    GENERATOR = "generator"        # Meta-skill for generating other skills
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    """Type of dependency edge."""
    DELEGATION = "delegation"      # One skill delegates to another
    DEPENDENCY = "dependency"      # One skill depends on another
    REFERENCE = "reference"        # One skill references another


@dataclass
class SkillNode:
    """Represents a skill node in the dependency graph.

    Attributes:
        name: Skill name (e.g., 'gcp-gcs-ops')
        node_type: Type of skill (ops, shared_framework, etc.)
        triggers: List of trigger keywords/phrases
        delegations: List of skills this skill delegates to
    """
    name: str
    node_type: NodeType = NodeType.OPS
    triggers: list[str] = field(default_factory=list)
    delegations: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        """Serialize node to dictionary."""
        return {
            "name": self.name,
            "node_type": self.node_type.value,
            "triggers": self.triggers,
            "delegations": self.delegations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillNode:
        """Create node from dictionary."""
        return cls(
            name=data["name"],
            node_type=NodeType(data.get("node_type", "ops")),
            triggers=data.get("triggers", []),
            delegations=data.get("delegations", []),
        )


@dataclass
class SkillEdge:
    """Represents a dependency edge between two skills.

    Attributes:
        source: Source skill name
        target: Target skill name
        edge_type: Type of relationship
        weight: Strength of relationship (0.0 - 1.0)
    """
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEPENDENCY
    weight: float = 0.5

    def model_dump(self) -> dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillEdge:
        """Create edge from dictionary."""
        return cls(
            source=data["source"],
            target=data["target"],
            edge_type=EdgeType(data.get("edge_type", "dependency")),
            weight=data.get("weight", 0.5),
        )


@dataclass
class SkillGraph:
    """Represents the complete skill dependency graph.

    Attributes:
        nodes: Dictionary mapping skill name to SkillNode
        edges: List of SkillEdge connections
    """
    nodes: dict[str, SkillNode] = field(default_factory=dict)
    edges: list[SkillEdge] = field(default_factory=list)

    def add_node(self, node: SkillNode) -> None:
        """Add a node to the graph if it doesn't already exist."""
        if node.name not in self.nodes:
            self.nodes[node.name] = node

    def add_edge(self, edge: SkillEdge) -> None:
        """Add an edge to the graph."""
        # Ensure both nodes exist
        if edge.source not in self.nodes:
            self.nodes[edge.source] = SkillNode(name=edge.source)
        if edge.target not in self.nodes:
            self.nodes[edge.target] = SkillNode(name=edge.target)
        self.edges.append(edge)

    def get_neighbors(self, node_name: str) -> set[str]:
        """Get all neighboring nodes (directly connected)."""
        neighbors: set[str] = set()
        for edge in self.edges:
            if edge.source == node_name:
                neighbors.add(edge.target)
            elif edge.target == node_name:
                neighbors.add(edge.source)
        return neighbors

    def get_outgoing_edges(self, node_name: str) -> list[SkillEdge]:
        """Get all outgoing edges from a node."""
        return [e for e in self.edges if e.source == node_name]

    def get_incoming_edges(self, node_name: str) -> list[SkillEdge]:
        """Get all incoming edges to a node."""
        return [e for e in self.edges if e.target == node_name]

    def model_dump(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": {name: node.model_dump() for name, node in self.nodes.items()},
            "edges": [edge.model_dump() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillGraph:
        """Create graph from dictionary."""
        graph = cls()
        for name, node_data in data.get("nodes", {}).items():
            graph.nodes[name] = SkillNode.from_dict(node_data)
        for edge_data in data.get("edges", []):
            graph.edges.append(SkillEdge.from_dict(edge_data))
        return graph
