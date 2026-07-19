#!/usr/bin/env python3
"""
Tests for AIOps self-healing closed loop: trace_feedback.py consumption.

Validates that traces emitted by AIOps runbooks (HALT escalation, dry-run
gating, degraded-to-human, multi-skill aggregation) are correctly consumed
and aggregated by trace_feedback.py. This closes the loop:
    eval_queries.json (trigger) -> runbook action -> emit trace -> aggregate.

Run with: python -m pytest tests/test_aiops_trace_feedback.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the gcl-runner-ops directory is in sys.path
GCL_RUNNER_OPS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(GCL_RUNNER_OPS_DIR))

from trace_feedback import (  # noqa: E402
    aggregate,
    build_report,
    main,
    scan_traces,
)


def _write_trace(tmp_dir: Path, name: str, payload: dict) -> Path:
    path = tmp_dir / name
    path.write_text(json.dumps(payload))
    return path


# --- AIOps self-healing trace fixtures (mirror runbook emit format) ---

# Dimension 2 (monitoring/logging/securitycenter/armor) — anomaly detection + mute
AIOps_MONITORING_PASS = {
    "trace_id": "aiops-mon-1",
    "timestamp": "2026-07-19T11:00:00Z",
    "skill": "gcp-monitoring-ops",
    "op": "SilenceIncident",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
}

AIOps_ARMOR_DRYRUN = {
    "trace_id": "aiops-armor-1",
    "timestamp": "2026-07-19T11:05:00Z",
    "skill": "gcp-armor-ops",
    "op": "DeployAdaptiveProtection",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
    "dry_run": True,
}

# Dimension 3 (cloudrun/composer/memorystore/cloudsql/gke/pubsub/bigquery) — self-heal
AIOps_CLOUDRUN_HALT = {
    "trace_id": "aiops-cr-1",
    "timestamp": "2026-07-19T11:10:00Z",
    "skill": "gcp-cloudrun-ops",
    "op": "RollbackRevision",
    "result": "HALT",  # human-review gate, not auto-applied
    "error_type": "HEALTHCHECK_FAIL",
    "safety_score": 1.0,
    "autonomy_ratio": 0.0,
    "degraded_to_human": True,
}

AIOps_GKE_PASS = {
    "trace_id": "aiops-gke-1",
    "timestamp": "2026-07-19T11:15:00Z",
    "skill": "gcp-gke-ops",
    "op": "EnableAutoRepair",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
}

AIOps_PUBSUB_DLQ = {
    "trace_id": "aiops-ps-1",
    "timestamp": "2026-07-19T11:20:00Z",
    "skill": "gcp-pubsub-ops",
    "op": "CreateDLQReplay",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
}

# Dimension 4 + CDN (gce/lb/dns/cloudfunctions/kms/secretmanager/filestore/cdn)
AIOps_GCE_PASS = {
    "trace_id": "aiops-gce-1",
    "timestamp": "2026-07-19T11:25:00Z",
    "skill": "gcp-gce-ops",
    "op": "RecreateInstance",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
}

AIOps_CDN_DRYRUN = {
    "trace_id": "aiops-cdn-1",
    "timestamp": "2026-07-19T11:30:00Z",
    "skill": "gcp-cdn-ops",
    "op": "InvalidateCache",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
    "dry_run": True,
}

AIOps_KMS_FAIL = {
    "trace_id": "aiops-kms-1",
    "timestamp": "2026-07-19T11:35:00Z",
    "skill": "gcp-kms-ops",
    "op": "RotateKey",
    "result": "ERROR",
    "error_type": "QUOTA_EXCEEDED",
    "safety_score": 1.0,
    "autonomy_ratio": 0.7,
}


ALL_AIOPS_TRACES = [
    AIOps_MONITORING_PASS,
    AIOps_ARMOR_DRYRUN,
    AIOps_CLOUDRUN_HALT,
    AIOps_GKE_PASS,
    AIOps_PUBSUB_DLQ,
    AIOps_GCE_PASS,
    AIOps_CDN_DRYRUN,
    AIOps_KMS_FAIL,
]


class TestAIOpsScanTraces:
    """AIOps traces follow the same gcl-trace-*.json naming and are picked up."""

    def test_aiops_traces_scanned(self, tmp_path: Path) -> None:
        for i, t in enumerate(ALL_AIOPS_TRACES):
            _write_trace(tmp_path, f"gcl-trace-aiops-{i}.json", t)
        traces = scan_traces(tmp_path)
        assert len(traces) == len(ALL_AIOPS_TRACES)

    def test_aiops_trace_with_dry_run_field_ignored_gracefully(self, tmp_path: Path) -> None:
        # dry_run is not a consumed field; trace must still aggregate without error
        _write_trace(tmp_path, "gcl-trace-dry.json", AIOps_ARMOR_DRYRUN)
        traces = scan_traces(tmp_path)
        assert len(traces) == 1
        assert traces[0]["skill"] == "gcp-armor-ops"


class TestAIOpsAggregate:
    """AIOps self-healing dimensions aggregate correctly."""

    def test_aggregates_all_aiops_skills(self) -> None:
        by_skill = aggregate(ALL_AIOPS_TRACES)
        # 8 distinct skills across dimensions 2/3/4+CDN
        assert set(by_skill) == {
            "gcp-monitoring-ops",
            "gcp-armor-ops",
            "gcp-cloudrun-ops",
            "gcp-gke-ops",
            "gcp-pubsub-ops",
            "gcp-gce-ops",
            "gcp-cdn-ops",
            "gcp-kms-ops",
        }

    def test_halt_counts_as_failure_but_not_safety_violation(self) -> None:
        by_skill = aggregate([AIOps_CLOUDRUN_HALT])
        q = by_skill["gcp-cloudrun-ops"]
        assert q.total == 1
        assert q.failures == 1  # HALT is non-PASS
        assert q.degraded_count == 1
        assert q.low_safety_count == 0  # safety_score 1.0 -> not flagged
        assert q.low_autonomy_count == 1  # autonomy_ratio 0.0 -> flagged

    def test_pass_rate_across_dimensions(self) -> None:
        by_skill = aggregate(ALL_AIOPS_TRACES)
        total = sum(q.total for q in by_skill.values())
        failures = sum(q.failures for q in by_skill.values())
        # 8 traces, 2 failures (HALT + ERROR)
        assert total == 8
        assert failures == 2
        assert (total - failures) / total == pytest.approx(0.75)


class TestAIOpsBuildReport:
    """Report surfaces AIOps failure dimensions (HALT, error_type)."""

    def test_report_includes_halt_and_error(self) -> None:
        by_skill = aggregate(ALL_AIOPS_TRACES)
        report = build_report(by_skill)
        assert "# GCL Skill Quality Report" in report
        assert "gcp-cloudrun-ops" in report
        assert "gcp-kms-ops" in report
        assert "HALT" in report
        assert "HEALTHCHECK_FAIL" in report
        assert "QUOTA_EXCEEDED" in report

    def test_report_empty(self) -> None:
        assert "No traces found" in build_report({})


class TestAIOpsMain:
    """End-to-end CLI consumes AIOps traces from a trace dir."""

    def test_main_aggregates_aiops(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        for i, t in enumerate(ALL_AIOPS_TRACES):
            _write_trace(tmp_path, f"gcl-trace-aiops-{i}.json", t)
        rc = main(["--trace-dir", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "gcp-armor-ops" in out
        assert "HALT" in out
        assert "75.0%" in out  # 6/8 pass rate

    def test_main_report_path_aiops(self, tmp_path: Path) -> None:
        _write_trace(tmp_path, "gcl-trace-halt.json", AIOps_CLOUDRUN_HALT)
        report_file = tmp_path / "aiops-report.md"
        rc = main(["--trace-dir", str(tmp_path), "--report-path", str(report_file)])
        assert rc == 0
        content = report_file.read_text()
        assert "gcp-cloudrun-ops" in content
        assert "HALT" in content
