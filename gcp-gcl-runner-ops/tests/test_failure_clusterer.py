#!/usr/bin/env python3
"""Tests for failure-pattern clustering over GCL trajectory classifications."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from failure_clusterer import (
    _signature,
    cluster_failures,
    cluster_traces,
)
from trajectory_classifier import Classification, TraceClass


def _c(
    trace_id: str, category: TraceClass, reason: str, source_file: str | None = None
) -> Classification:
    """Helper: build a Classification without a GCLTrace."""
    return Classification(
        trace_id=trace_id, category=category, reason=reason, source_file=source_file
    )


def test_cluster_failures_empty() -> None:
    """Empty input → empty clusters."""
    assert cluster_failures([]) == []


def test_cluster_skips_success() -> None:
    """SUCCESS is excluded; only the FAILURE cluster remains."""
    items = [
        _c("t1", TraceClass.SUCCESS, "all quality gates passed"),
        _c("t2", TraceClass.FAILURE, "exit_code=1"),
    ]
    clusters = cluster_failures(items)
    assert len(clusters) == 1
    assert clusters[0].label == "Non-zero exit"
    assert all(c.category != TraceClass.SUCCESS for c in clusters)


def test_cluster_groups_same_signature() -> None:
    """Two latency reasons with different numbers collapse to one cluster."""
    items = [
        _c("t1", TraceClass.ANOMALY, "latency_ms=120000 > 60000"),
        _c("t2", TraceClass.ANOMALY, "latency_ms=90000 > 60000"),
    ]
    clusters = cluster_failures(items)
    assert len(clusters) == 1
    assert clusters[0].count == 2


def test_cluster_separates_distinct() -> None:
    """Safety failure and exit_code are distinct signatures → 2 clusters."""
    items = [
        _c("t1", TraceClass.FAILURE, "result=SAFETY_FAIL"),
        _c("t2", TraceClass.FAILURE, "exit_code=1"),
    ]
    clusters = cluster_failures(items)
    assert len(clusters) == 2


def test_cluster_label_readable() -> None:
    """Latency cluster gets a friendly label."""
    items = [_c("t1", TraceClass.ANOMALY, "latency_ms=120000 > 60000")]
    clusters = cluster_failures(items)
    assert clusters[0].label == "High latency"


def test_cluster_sorted_by_count() -> None:
    """Clusters returned sorted by count DESC."""
    items = [
        _c("a1", TraceClass.FAILURE, "exit_code=1"),
        _c("a2", TraceClass.FAILURE, "exit_code=2"),
        _c("a3", TraceClass.FAILURE, "exit_code=3"),
        _c("b1", TraceClass.FAILURE, "result=SAFETY_FAIL"),
    ]
    clusters = cluster_failures(items)
    assert len(clusters) == 2
    assert clusters[0].count == 3
    assert clusters[1].count == 1


def test_signature_strips_numbers() -> None:
    """_signature replaces digit runs with THRESHOLD and drops spaces."""
    assert _signature("latency_ms=120000 > 60000") == "latency_ms>THRESHOLD"


def test_cluster_members() -> None:
    """Cluster.members collects the trace_ids."""
    items = [
        _c("t1", TraceClass.ANOMALY, "latency_ms=120000 > 60000"),
        _c("t2", TraceClass.ANOMALY, "latency_ms=90000 > 60000"),
    ]
    clusters = cluster_failures(items)
    assert set(clusters[0].members) == {"t1", "t2"}


def test_cluster_traces_missing_dir() -> None:
    """Missing directory → [] without raising."""
    assert cluster_traces("/no/such/dir") == []


def test_category_preserved() -> None:
    """Cluster keeps the TraceClass of its members."""
    items = [_c("t1", TraceClass.ANOMALY, "latency_ms=120000 > 60000")]
    clusters = cluster_failures(items)
    assert clusters[0].category == TraceClass.ANOMALY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
