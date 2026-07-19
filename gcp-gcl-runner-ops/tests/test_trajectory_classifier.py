#!/usr/bin/env python3
"""
Tests for trajectory auto-classification (SUCCESS/FAILURE/ANOMALY).

Run with: python -m pytest tests/test_trajectory_classifier.py -v
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gcl_trace_schema import Environment, GCLResult, GCLTrace
from trajectory_classifier import (
    AUTONOMY_ANOMALY_MIN,
    ITER_ANOMALY_COUNT,
    LATENCY_ANOMALY_MS,
    TraceClass,
    classify_directory,
    classify_trace,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def base_trace() -> GCLTrace:
    """Base success trace used as a template for variations."""
    return GCLTrace(
        trace_id="gcl-trace-20260718-143052-abc123",
        timestamp=datetime.now(UTC).isoformat(),
        skill="gcp-gce-ops",
        op="DeleteInstance",
        result=GCLResult.PASS,
        exit_code=0,
        latency_ms=4523,
        iterations_count=2,
        autonomy_ratio=0.75,
        safety_score=1.0,
        safety_failures=0,
        error_type=None,
        degraded_to_human=False,
        environment=Environment.PRODUCTION,
    )


# ── classify_trace tests ──────────────────────────────────────────────────────


def test_classify_success_pass(base_trace: GCLTrace) -> None:
    """PASS + safety 1.0 → SUCCESS."""
    c = classify_trace(base_trace)
    assert c.category == TraceClass.SUCCESS
    assert c.trace_id == base_trace.trace_id


def test_classify_safety_fail(base_trace: GCLTrace) -> None:
    """SAFETY_FAIL OR safety_score 0.0 → FAILURE."""
    t1 = GCLTrace(**{**asdict(base_trace), "result": GCLResult.SAFETY_FAIL})
    assert classify_trace(t1).category == TraceClass.FAILURE

    t2 = GCLTrace(**{**asdict(base_trace), "safety_score": 0.0})
    assert classify_trace(t2).category == TraceClass.FAILURE


def test_classify_max_iter(base_trace: GCLTrace) -> None:
    """result MAX_ITER → FAILURE (NOT anomaly)."""
    t = GCLTrace(**{**asdict(base_trace), "result": GCLResult.MAX_ITER})
    c = classify_trace(t)
    assert c.category == TraceClass.FAILURE


def test_classify_exit_code(base_trace: GCLTrace) -> None:
    """exit_code != 0 → FAILURE."""
    t = GCLTrace(**{**asdict(base_trace), "exit_code": 1})
    c = classify_trace(t)
    assert c.category == TraceClass.FAILURE
    assert "exit_code=1" in c.reason


def test_classify_anomaly_degraded(base_trace: GCLTrace) -> None:
    """degraded_to_human=True → ANOMALY."""
    t = GCLTrace(**{**asdict(base_trace), "degraded_to_human": True})
    c = classify_trace(t)
    assert c.category == TraceClass.ANOMALY
    assert "degraded_to_human=True" in c.reason


def test_classify_anomaly_latency(base_trace: GCLTrace) -> None:
    """latency_ms 120000 → ANOMALY."""
    t = GCLTrace(**{**asdict(base_trace), "latency_ms": 120000})
    c = classify_trace(t)
    assert c.category == TraceClass.ANOMALY
    assert f"latency_ms=120000 > {LATENCY_ANOMALY_MS}" in c.reason


def test_classify_anomaly_iterations(base_trace: GCLTrace) -> None:
    """iterations_count >= ITER_ANOMALY_COUNT → ANOMALY."""
    t = GCLTrace(**{**asdict(base_trace), "iterations_count": ITER_ANOMALY_COUNT})
    c = classify_trace(t)
    assert c.category == TraceClass.ANOMALY
    assert f"iterations_count={ITER_ANOMALY_COUNT} >= {ITER_ANOMALY_COUNT}" in c.reason


def test_classify_anomaly_low_autonomy(base_trace: GCLTrace) -> None:
    """autonomy_ratio 0.2 → ANOMALY."""
    t = GCLTrace(**{**asdict(base_trace), "autonomy_ratio": 0.2})
    c = classify_trace(t)
    assert c.category == TraceClass.ANOMALY
    assert f"autonomy_ratio=0.2 < {AUTONOMY_ANOMALY_MIN}" in c.reason


def test_classify_anomaly_error_type(base_trace: GCLTrace) -> None:
    """error_type set → ANOMALY."""
    t = GCLTrace(**{**asdict(base_trace), "error_type": "TIMEOUT"})
    c = classify_trace(t)
    assert c.category == TraceClass.ANOMALY
    assert "error_type=TIMEOUT" in c.reason


def test_first_match_priority(base_trace: GCLTrace) -> None:
    """SAFETY_FAIL + degraded_to_human → still FAILURE (priority over anomaly)."""
    t = GCLTrace(
        **{**asdict(base_trace), "result": GCLResult.SAFETY_FAIL, "degraded_to_human": True}
    )
    c = classify_trace(t)
    assert c.category == TraceClass.FAILURE


def test_reason_nonempty(base_trace: GCLTrace) -> None:
    """Every Classification has a non-empty reason."""
    variants = [
        base_trace,
        GCLTrace(**{**asdict(base_trace), "result": GCLResult.SAFETY_FAIL}),
        GCLTrace(**{**asdict(base_trace), "result": GCLResult.MAX_ITER}),
        GCLTrace(**{**asdict(base_trace), "exit_code": 1}),
        GCLTrace(**{**asdict(base_trace), "degraded_to_human": True}),
        GCLTrace(**{**asdict(base_trace), "latency_ms": 120000}),
        GCLTrace(**{**asdict(base_trace), "autonomy_ratio": 0.2}),
        GCLTrace(**{**asdict(base_trace), "error_type": "TIMEOUT"}),
    ]
    for t in variants:
        assert classify_trace(t).reason.strip()


# ── classify_directory tests ──────────────────────────────────────────────────


def test_classify_directory(tmp_path: Path, base_trace: GCLTrace) -> None:
    """Two sample JSON files → 2 correct classifications with source_file set."""
    success = GCLTrace(**asdict(base_trace))
    failure = GCLTrace(**{**asdict(base_trace), "result": GCLResult.SAFETY_FAIL})

    (tmp_path / "gcl-trace-001.json").write_text(json.dumps(asdict(success)))
    (tmp_path / "gcl-trace-002.json").write_text(json.dumps(asdict(failure)))

    results = classify_directory(tmp_path)
    assert len(results) == 2

    by_file = {c.source_file: c for c in results}
    assert by_file["gcl-trace-001.json"].category == TraceClass.SUCCESS
    assert by_file["gcl-trace-002.json"].category == TraceClass.FAILURE


def test_classify_directory_missing(tmp_path: Path) -> None:
    """Nonexistent path → [] without raising."""
    missing = tmp_path / "does-not-exist"
    assert classify_directory(missing) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
