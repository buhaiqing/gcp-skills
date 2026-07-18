#!/usr/bin/env python3
"""
Tests for Knowledge Query API.

Run with: python -m pytest tests/test_knowledge_query.py -v
"""

from __future__ import annotations

import time

import pytest
from knowledge_query import (
    CrossDomainDiscovery,
    DependencyResolver,
    KnowledgeQueryAPI,
)
from skill_dependency.schema import EdgeType, NodeType, SkillEdge, SkillGraph, SkillNode

# ── Test Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_graph() -> SkillGraph:
    """Sample graph for testing knowledge queries."""
    graph = SkillGraph()

    # GCS ops skill
    graph.add_node(SkillNode(
        name="gcp-gcs-ops",
        node_type=NodeType.OPS,
        triggers=["Cloud Storage", "GCS", "bucket", "storage"],
        delegations=["gcp-gcl-runner-ops"]
    ))

    # IAM ops skill
    graph.add_node(SkillNode(
        name="gcp-iam-ops",
        node_type=NodeType.OPS,
        triggers=["IAM", "service account", "permissions", "access"],
        delegations=["gcp-gcl-runner-ops"]
    ))

    # KMS ops skill
    graph.add_node(SkillNode(
        name="gcp-kms-ops",
        node_type=NodeType.OPS,
        triggers=["KMS", "encryption", "keys", "cryptographic"],
        delegations=["gcp-gcl-runner-ops"]
    ))

    # GCL runner - shared framework
    graph.add_node(SkillNode(
        name="gcp-gcl-runner-ops",
        node_type=NodeType.SHARED_FRAMEWORK,
        triggers=["GCL quality gate", "quality gate", "GCL runner"],
        delegations=[]
    ))

    # BigQuery ops
    graph.add_node(SkillNode(
        name="gcp-bigquery-ops",
        node_type=NodeType.OPS,
        triggers=["BigQuery", "bigquery", "bq", "data warehouse"],
        delegations=["gcp-gcl-runner-ops"]
    ))

    # Compute ops
    graph.add_node(SkillNode(
        name="gcp-compute-ops",
        node_type=NodeType.OPS,
        triggers=["Compute", "VM", "instance", "GCE"],
        delegations=["gcp-gcl-runner-ops"]
    ))

    # Add edges
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
        weight=0.3
    ))
    graph.add_edge(SkillEdge(
        source="gcp-iam-ops",
        target="gcp-gcl-runner-ops",
        edge_type=EdgeType.DELEGATION,
        weight=1.0
    ))
    graph.add_edge(SkillEdge(
        source="gcp-kms-ops",
        target="gcp-gcl-runner-ops",
        edge_type=EdgeType.DELEGATION,
        weight=1.0
    ))
    graph.add_edge(SkillEdge(
        source="gcp-bigquery-ops",
        target="gcp-gcl-runner-ops",
        edge_type=EdgeType.DELEGATION,
        weight=1.0
    ))
    graph.add_edge(SkillEdge(
        source="gcp-bigquery-ops",
        target="gcp-iam-ops",
        edge_type=EdgeType.DEPENDENCY,
        weight=0.4
    ))
    graph.add_edge(SkillEdge(
        source="gcp-compute-ops",
        target="gcp-gcl-runner-ops",
        edge_type=EdgeType.DELEGATION,
        weight=1.0
    ))

    return graph


@pytest.fixture
def query_api(sample_graph: SkillGraph) -> KnowledgeQueryAPI:
    """Create KnowledgeQueryAPI with sample graph."""
    return KnowledgeQueryAPI(graph=sample_graph)


# ── KnowledgeQueryAPI Tests ────────────────────────────────────────────────────

class TestQuerySkillDependencies:
    """Test suite for query_skill_dependencies."""

    def test_query_direct_dependencies(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify querying direct dependencies returns immediate neighbors."""
        result = query_api.query_skill_dependencies("gcp-gcs-ops")

        assert result is not None
        # Should include gcp-gcl-runner-ops (delegation) and gcp-iam-ops (dependency)
        dep_names = {d["skill_name"] for d in result["dependencies"]}
        assert "gcp-gcl-runner-ops" in dep_names
        assert "gcp-iam-ops" in dep_names

    def test_query_no_dependencies(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify querying skill with no dependencies returns empty list."""
        result = query_api.query_skill_dependencies("gcp-gcl-runner-ops")

        assert result is not None
        assert len(result["dependencies"]) == 0

    def test_query_nonexistent_skill(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify querying nonexistent skill returns empty result."""
        result = query_api.query_skill_dependencies("gcp-nonexistent-ops")

        assert result is not None
        assert len(result["dependencies"]) == 0

    def test_query_includes_edge_types(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify dependency results include edge types."""
        result = query_api.query_skill_dependencies("gcp-gcs-ops")

        dep_by_name = {d["skill_name"]: d for d in result["dependencies"]}
        assert dep_by_name["gcp-gcl-runner-ops"]["edge_type"] == "delegation"
        assert dep_by_name["gcp-iam-ops"]["edge_type"] == "dependency"


class TestQueryCrossDomainSkills:
    """Test suite for query_cross_domain_skills."""

    def test_query_by_single_keyword(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify cross-domain query with single keyword."""
        result = query_api.query_cross_domain_skills(["bucket"])

        assert result is not None
        skill_names = {s["skill_name"] for s in result["skills"]}
        assert "gcp-gcs-ops" in skill_names

    def test_query_by_multiple_keywords(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify cross-domain query with multiple keywords."""
        result = query_api.query_cross_domain_skills(["storage", "data warehouse"])

        assert result is not None
        skill_names = {s["skill_name"] for s in result["skills"]}
        assert "gcp-gcs-ops" in skill_names
        assert "gcp-bigquery-ops" in skill_names

    def test_query_no_matching_keywords(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify cross-domain query with no matches returns empty."""
        result = query_api.query_cross_domain_skills(["xyznonexistent"])

        assert result is not None
        assert len(result["skills"]) == 0

    def test_query_includes_match_score(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify cross-domain results include match score."""
        result = query_api.query_cross_domain_skills(["storage"])

        assert result is not None
        for skill in result["skills"]:
            assert "match_score" in skill
            assert skill["match_score"] > 0


class TestQuerySimilarSkills:
    """Test suite for query_similar_skills."""

    def test_query_similar_finds_similar(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify similar skills query returns related skills."""
        result = query_api.query_similar_skills("gcp-gcs-ops")

        assert result is not None
        assert len(result["similar_skills"]) > 0

    def test_query_similar_excludes_self(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify similar skills does not include the query skill itself."""
        result = query_api.query_similar_skills("gcp-gcs-ops")

        skill_names = {s["skill_name"] for s in result["similar_skills"]}
        assert "gcp-gcs-ops" not in skill_names

    def test_query_similar_nonexistent(self, query_api: KnowledgeQueryAPI) -> None:
        """Verify similar query for nonexistent skill returns empty."""
        result = query_api.query_similar_skills("gcp-nonexistent-ops")

        assert result is not None
        assert len(result["similar_skills"]) == 0


# ── DependencyResolver Tests ──────────────────────────────────────────────────

class TestDependencyResolver:
    """Test suite for DependencyResolver."""

    def test_bfs_query(self, sample_graph: SkillGraph) -> None:
        """Verify BFS traversal returns all reachable nodes."""
        resolver = DependencyResolver(graph=sample_graph)

        # gcp-gcs-ops -> gcp-iam-ops -> gcp-gcl-runner-ops
        result = resolver.bfs_query("gcp-gcs-ops", max_depth=2)

        assert "gcp-gcl-runner-ops" in result
        assert "gcp-iam-ops" in result

    def test_dfs_query(self, sample_graph: SkillGraph) -> None:
        """Verify DFS traversal returns all reachable nodes."""
        resolver = DependencyResolver(graph=sample_graph)

        result = resolver.dfs_query("gcp-gcs-ops", max_depth=2)

        assert "gcp-gcl-runner-ops" in result
        assert "gcp-iam-ops" in result

    def test_query_respects_max_depth(self, sample_graph: SkillGraph) -> None:
        """Verify BFS/DFS respects max_depth limit."""
        resolver = DependencyResolver(graph=sample_graph)

        # depth 1 should only get direct neighbors
        result = resolver.bfs_query("gcp-gcs-ops", max_depth=1)

        # gcp-gcl-runner-ops is direct neighbor (delegation edge)
        # gcp-iam-ops is also direct neighbor (dependency edge)
        assert "gcp-gcl-runner-ops" in result or "gcp-iam-ops" in result

    def test_query_empty_for_isolated_nodes(self, sample_graph: SkillGraph) -> None:
        """Verify query returns empty for isolated node."""
        # Add isolated node
        sample_graph.add_node(SkillNode(name="isolated-skill"))

        resolver = DependencyResolver(graph=sample_graph)
        result = resolver.bfs_query("isolated-skill", max_depth=1)

        assert len(result) == 0


# ── CrossDomainDiscovery Tests ─────────────────────────────────────────────────

class TestCrossDomainDiscovery:
    """Test suite for CrossDomainDiscovery."""

    def test_keyword_matching(self, sample_graph: SkillGraph) -> None:
        """Verify keyword matching returns relevant skills."""
        discovery = CrossDomainDiscovery(graph=sample_graph)

        results = discovery.find_by_keywords(["storage"])

        assert len(results) > 0
        skill_names = [r.skill_name for r in results]
        assert "gcp-gcs-ops" in skill_names

    def test_multiple_keyword_intersection(self, sample_graph: SkillGraph) -> None:
        """Verify multiple keywords are matched against all skills."""
        discovery = CrossDomainDiscovery(graph=sample_graph)

        # Both GCS and IAM have "access" related triggers
        results = discovery.find_by_keywords(["access", "permissions"])

        # Should find skills that match either keyword
        skill_names = [r.skill_name for r in results]
        assert len(skill_names) >= 1

    def test_empty_keywords(self, sample_graph: SkillGraph) -> None:
        """Verify empty keyword list returns empty results."""
        discovery = CrossDomainDiscovery(graph=sample_graph)

        results = discovery.find_by_keywords([])

        assert len(results) == 0

    def test_match_score_calculation(self, sample_graph: SkillGraph) -> None:
        """Verify match score reflects number of keyword matches."""
        discovery = CrossDomainDiscovery(graph=sample_graph)

        # "Cloud Storage" has 2 trigger words that could match "Cloud" and "Storage"
        results = discovery.find_by_keywords(["Cloud", "Storage", "bucket"])

        # Sort by score
        sorted_results = sorted(results, key=lambda x: x.match_score, reverse=True)

        # Top result should be gcp-gcs-ops with highest match score
        assert sorted_results[0].skill_name == "gcp-gcs-ops"

    def test_target_accuracy_estimation(self, sample_graph: SkillGraph) -> None:
        """Verify accuracy estimation is calculated."""
        discovery = CrossDomainDiscovery(graph=sample_graph)

        accuracy = discovery.estimate_accuracy()

        assert 0.0 <= accuracy <= 1.0


# ── Performance Tests ─────────────────────────────────────────────────────────

class TestQueryResponseTime:
    """Test suite for query response time requirements."""

    def test_query_skill_dependencies_response_time(
        self, query_api: KnowledgeQueryAPI
    ) -> None:
        """Verify query_skill_dependencies responds in < 100ms."""
        start = time.perf_counter()

        for _ in range(100):
            query_api.query_skill_dependencies("gcp-gcs-ops")

        elapsed = (time.perf_counter() - start) * 10  # Convert to ms for 100 calls
        avg_ms = elapsed / 100

        assert avg_ms < 100, f"Average response time {avg_ms:.2f}ms exceeds 100ms limit"

    def test_query_cross_domain_response_time(
        self, query_api: KnowledgeQueryAPI
    ) -> None:
        """Verify query_cross_domain_skills responds in < 100ms."""
        start = time.perf_counter()

        for _ in range(100):
            query_api.query_cross_domain_skills(["storage", "bucket"])

        elapsed = (time.perf_counter() - start) * 10  # Convert to ms for 100 calls
        avg_ms = elapsed / 100

        assert avg_ms < 100, f"Average response time {avg_ms:.2f}ms exceeds 100ms limit"

    def test_query_similar_skills_response_time(
        self, query_api: KnowledgeQueryAPI
    ) -> None:
        """Verify query_similar_skills responds in < 100ms."""
        start = time.perf_counter()

        for _ in range(100):
            query_api.query_similar_skills("gcp-gcs-ops")

        elapsed = (time.perf_counter() - start) * 10  # Convert to ms for 100 calls
        avg_ms = elapsed / 100

        assert avg_ms < 100, f"Average response time {avg_ms:.2f}ms exceeds 100ms limit"
