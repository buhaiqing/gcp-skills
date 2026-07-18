#!/usr/bin/env python3
"""
Tests for Skill Dependency Mapping.

Run with: python -m pytest tests/test_skill_dependency.py -v
"""

from __future__ import annotations

from typing import Any

import pytest

from skill_dependency.schema import SkillNode, SkillEdge, SkillGraph, EdgeType, NodeType
from skill_dependency.extractor import DependencyExtractor
from skill_dependency.storage import GraphStorage
from skill_dependency.visualizer import MermaidVisualizer


# ── Test Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_skill_md() -> str:
    """Sample SKILL.md content for testing extraction."""
    return """---
name: gcp-gcs-ops
description: >-
  Use when the user needs to manage Google Cloud Storage.
---

# Google Cloud Storage Operations Skill

## Trigger & Scope

### SHOULD Use When
- User mentions "Cloud Storage", "GCS", "bucket"

### SHOULD NOT Use When
- IAM to gcp-iam-ops; KMS to gcp-kms-ops

## Delegation Rules

| Source Skill Type | Trigger | Context Passed |
|-------------------|---------|----------------|
| All required skills | Before GCL quality gate | skill, op, command |
| gcp-skill-generator | When validating generated content | skill, op |
| gcp-gcs-ops | Delegates to gcp-gcl-runner-ops | GCL execution |

## Capabilities

| Operation | CLI Tool | Risk |
|-----------|----------|------|
| Create Bucket | gcloud storage | Low |
| Delete Bucket | gcloud storage | High |
"""


@pytest.fixture
def sample_graph() -> SkillGraph:
    """Sample graph for testing storage and visualization."""
    graph = SkillGraph()
    graph.add_node(SkillNode(
        name="gcp-gcs-ops",
        node_type=NodeType.OPS,
        triggers=["Cloud Storage", "GCS", "bucket"],
        delegations=["gcp-gcl-runner-ops"]
    ))
    graph.add_node(SkillNode(
        name="gcp-gcl-runner-ops",
        node_type=NodeType.SHARED_FRAMEWORK,
        triggers=["GCL quality gate"],
        delegations=[]
    ))
    graph.add_node(SkillNode(
        name="gcp-iam-ops",
        node_type=NodeType.OPS,
        triggers=["IAM", "service account", "permissions"],
        delegations=[]
    ))
    graph.add_edge(SkillEdge(
        source="gcp-gcs-ops",
        target="gcp-gcl-runner-ops",
        edge_type=EdgeType.DELEGATION,
        weight=1.0
    ))
    graph.add_edge(SkillEdge(
        source="gcp-gcs-ops",
        target="gcp-iam-ops",
        edge_type=EdgeType.DEPENDENCY,
        weight=0.5
    ))
    return graph


# ── Schema Tests ───────────────────────────────────────────────────────────────

class TestSkillNode:
    """Test suite for SkillNode creation and validation."""

    def test_skill_node_creation(self) -> None:
        """Verify SkillNode can be created with all required fields."""
        node = SkillNode(
            name="gcp-gcs-ops",
            node_type=NodeType.OPS,
            triggers=["Cloud Storage", "GCS", "bucket"],
            delegations=["gcp-gcl-runner-ops"]
        )
        assert node.name == "gcp-gcs-ops"
        assert node.node_type == NodeType.OPS
        assert node.triggers == ["Cloud Storage", "GCS", "bucket"]
        assert node.delegations == ["gcp-gcl-runner-ops"]

    def test_skill_node_defaults(self) -> None:
        """Verify SkillNode has sensible defaults."""
        node = SkillNode(name="gcp-test-ops")
        assert node.node_type == NodeType.OPS
        assert node.triggers == []
        assert node.delegations == []

    def test_skill_node_serialization(self) -> None:
        """Verify SkillNode serializes to dict correctly."""
        node = SkillNode(
            name="gcp-gcs-ops",
            node_type=NodeType.OPS,
            triggers=["Cloud Storage"],
            delegations=["gcp-gcl-runner-ops"]
        )
        data = node.model_dump()
        assert data["name"] == "gcp-gcs-ops"
        assert data["node_type"] == "ops"
        assert data["triggers"] == ["Cloud Storage"]
        assert data["delegations"] == ["gcp-gcl-runner-ops"]


class TestSkillEdge:
    """Test suite for SkillEdge creation and validation."""

    def test_skill_edge_creation(self) -> None:
        """Verify SkillEdge can be created with all required fields."""
        edge = SkillEdge(
            source="gcp-gcs-ops",
            target="gcp-gcl-runner-ops",
            edge_type=EdgeType.DELEGATION,
            weight=1.0
        )
        assert edge.source == "gcp-gcs-ops"
        assert edge.target == "gcp-gcl-runner-ops"
        assert edge.edge_type == EdgeType.DELEGATION
        assert edge.weight == 1.0

    def test_skill_edge_defaults(self) -> None:
        """Verify SkillEdge has sensible defaults."""
        edge = SkillEdge(source="a", target="b")
        assert edge.edge_type == EdgeType.DEPENDENCY
        assert edge.weight == 0.5

    def test_skill_edge_serialization(self) -> None:
        """Verify SkillEdge serializes to dict correctly."""
        edge = SkillEdge(
            source="gcp-gcs-ops",
            target="gcp-iam-ops",
            edge_type=EdgeType.DEPENDENCY,
            weight=0.7
        )
        data = edge.model_dump()
        assert data["source"] == "gcp-gcs-ops"
        assert data["target"] == "gcp-iam-ops"
        assert data["edge_type"] == "dependency"
        assert data["weight"] == 0.7


class TestSkillGraph:
    """Test suite for SkillGraph operations."""

    def test_graph_add_node(self) -> None:
        """Verify nodes can be added to graph."""
        graph = SkillGraph()
        node = SkillNode(name="gcp-gcs-ops", node_type=NodeType.OPS)
        graph.add_node(node)
        assert "gcp-gcs-ops" in graph.nodes

    def test_graph_add_edge(self) -> None:
        """Verify edges can be added to graph."""
        graph = SkillGraph()
        graph.add_node(SkillNode(name="a"))
        graph.add_node(SkillNode(name="b"))
        graph.add_edge(SkillEdge(source="a", target="b"))
        assert len(graph.edges) == 1

    def test_graph_no_duplicate_nodes(self) -> None:
        """Verify adding duplicate node does not overwrite."""
        graph = SkillGraph()
        node1 = SkillNode(name="gcp-gcs-ops", node_type=NodeType.OPS)
        node2 = SkillNode(name="gcp-gcs-ops", node_type=NodeType.SHARED_FRAMEWORK)
        graph.add_node(node1)
        graph.add_node(node2)  # Should not overwrite
        assert graph.nodes["gcp-gcs-ops"].node_type == NodeType.OPS

    def test_graph_get_neighbors(self) -> None:
        """Verify getting neighbors of a node."""
        graph = SkillGraph()
        graph.add_node(SkillNode(name="a"))
        graph.add_node(SkillNode(name="b"))
        graph.add_edge(SkillEdge(source="a", target="b"))
        neighbors = graph.get_neighbors("a")
        assert "b" in neighbors


# ── Extractor Tests ────────────────────────────────────────────────────────────

class TestDependencyExtractor:
    """Test suite for DependencyExtractor."""

    def test_extractor_parses_delegation_rules(self, sample_skill_md: str) -> None:
        """Verify extractor can parse delegation rules from SKILL.md."""
        extractor = DependencyExtractor()
        nodes, edges = extractor.extract(sample_skill_md)

        # Should find the main skill node
        assert "gcp-gcs-ops" in nodes
        assert nodes["gcp-gcs-ops"].name == "gcp-gcs-ops"

        # Should find some edges (may be dependency or delegation)
        assert len(edges) >= 1

    def test_extractor_parses_triggers(self, sample_skill_md: str) -> None:
        """Verify extractor can parse trigger conditions."""
        extractor = DependencyExtractor()
        nodes, _ = extractor.extract(sample_skill_md)

        triggers = nodes["gcp-gcs-ops"].triggers
        assert "Cloud Storage" in triggers
        assert "GCS" in triggers
        assert "bucket" in triggers

    def test_extractor_parses_skill_name(self, sample_skill_md: str) -> None:
        """Verify extractor extracts skill name from frontmatter."""
        extractor = DependencyExtractor()
        nodes, _ = extractor.extract(sample_skill_md)

        assert "gcp-gcs-ops" in nodes

    def test_extractor_handles_minimal_skill(self) -> None:
        """Verify extractor handles minimal SKILL.md without delegations."""
        minimal_md = """---
name: gcp-minimal-ops
---

# Minimal Skill

## Trigger & Scope

### SHOULD Use When
- User mentions "minimal"
"""
        extractor = DependencyExtractor()
        nodes, edges = extractor.extract(minimal_md)

        assert "gcp-minimal-ops" in nodes
        assert "minimal" in nodes["gcp-minimal-ops"].triggers
        assert len(edges) == 0

    def test_extractor_from_file(self, tmp_path: Any) -> None:
        """Verify extractor can read from file path."""
        skill_file = tmp_path / "test_skill.md"
        skill_file.write_text("""---
name: gcp-file-ops
---

# Test Skill

## Trigger & Scope

### SHOULD Use When
- User mentions "file"
""")
        extractor = DependencyExtractor()
        nodes, _ = extractor.extract(str(skill_file))

        assert "gcp-file-ops" in nodes


# ── Storage Tests ──────────────────────────────────────────────────────────────

class TestGraphStorage:
    """Test suite for GraphStorage."""

    def test_storage_save_and_load(self, sample_graph: SkillGraph, tmp_path: Any) -> None:
        """Verify graph can be saved to and loaded from JSON file."""
        storage_path = tmp_path / "graph.json"
        storage = GraphStorage(storage_path)

        # Save
        storage.save(sample_graph)

        # Load
        loaded_graph = storage.load()

        assert len(loaded_graph.nodes) == len(sample_graph.nodes)
        assert len(loaded_graph.edges) == len(sample_graph.edges)
        assert "gcp-gcs-ops" in loaded_graph.nodes
        assert "gcp-gcl-runner-ops" in loaded_graph.nodes

    def test_storage_load_nonexistent(self, tmp_path: Any) -> None:
        """Verify loading nonexistent file returns empty graph."""
        storage_path = tmp_path / "nonexistent.json"
        storage = GraphStorage(storage_path)
        graph = storage.load()

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_storage_overwrite(self, sample_graph: SkillGraph, tmp_path: Any) -> None:
        """Verify saving twice overwrites previous data."""
        storage_path = tmp_path / "graph.json"
        storage = GraphStorage(storage_path)

        storage.save(sample_graph)
        empty_graph = SkillGraph()
        storage.save(empty_graph)

        loaded = storage.load()
        assert len(loaded.nodes) == 0


# ── Visualizer Tests ───────────────────────────────────────────────────────────

class TestMermaidVisualizer:
    """Test suite for MermaidVisualizer."""

    def test_visualizer_generates_mermaid(self, sample_graph: SkillGraph) -> None:
        """Verify visualizer generates valid Mermaid code."""
        visualizer = MermaidVisualizer()
        mermaid_code = visualizer.generate(sample_graph)

        assert "graph TD" in mermaid_code
        assert "gcp-gcs-ops" in mermaid_code
        assert "gcp-gcl-runner-ops" in mermaid_code

    def test_visualizer_edge_labels(self, sample_graph: SkillGraph) -> None:
        """Verify Mermaid code contains edge labels."""
        visualizer = MermaidVisualizer()
        mermaid_code = visualizer.generate(sample_graph)

        assert "DELEGATION" in mermaid_code or "delegation" in mermaid_code.lower()
        assert "DEP" in mermaid_code or "dependency" in mermaid_code.lower()

    def test_visualizer_empty_graph(self) -> None:
        """Verify visualizer handles empty graph."""
        graph = SkillGraph()
        visualizer = MermaidVisualizer()
        mermaid_code = visualizer.generate(graph)

        assert "graph TD" in mermaid_code

    def test_visualizer_saves_to_file(self, sample_graph: SkillGraph, tmp_path: Any) -> None:
        """Verify visualizer can save Mermaid code to file."""
        output_path = tmp_path / "graph.mmd"
        visualizer = MermaidVisualizer()
        visualizer.generate(sample_graph, output_path=str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "graph TD" in content


# ── Integration Tests ──────────────────────────────────────────────────────────

class TestFullPipeline:
    """Integration tests for the full extract-store-visualize pipeline."""

    def test_full_pipeline(self, sample_skill_md: str, tmp_path: Any) -> None:
        """Verify full pipeline: extract -> store -> visualize."""
        # Extract
        extractor = DependencyExtractor()
        nodes, edges = extractor.extract(sample_skill_md)

        # Build graph
        graph = SkillGraph()
        for node in nodes.values():
            graph.add_node(node)
        for edge in edges:
            graph.add_edge(edge)

        # Store
        storage_path = tmp_path / "test_graph.json"
        storage = GraphStorage(storage_path)
        storage.save(graph)

        # Load
        loaded_graph = storage.load()

        # Visualize
        visualizer = MermaidVisualizer()
        mermaid_code = visualizer.generate(loaded_graph)

        assert "gcp-gcs-ops" in mermaid_code
        assert len(loaded_graph.nodes) > 0
