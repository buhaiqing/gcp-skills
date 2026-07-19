#!/usr/bin/env python3
"""
Tests for trace_feedback.py — GCL trace aggregation into skill quality report.

Run with: python -m pytest tests/test_trace_feedback.py -q
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
    parse_args,
    scan_traces,
)


def _write_trace(tmp_dir: Path, name: str, payload: dict) -> Path:
    path = tmp_dir / name
    path.write_text(json.dumps(payload))
    return path


PASS_TRACE = {
    "trace_id": "t-pass-1",
    "timestamp": "2026-07-19T10:00:00Z",
    "skill": "gcp-gce-ops",
    "op": "CreateInstance",
    "result": "PASS",
    "safety_score": 1.0,
    "autonomy_ratio": 1.0,
}

FAIL_SAFETY_TRACE = {
    "trace_id": "t-fail-1",
    "timestamp": "2026-07-19T10:05:00Z",
    "skill": "gcp-gce-ops",
    "op": "DeleteInstance",
    "result": "SAFETY_FAIL",
    "error_type": "PERMISSION_DENIED",
    "safety_score": 0.0,
    "autonomy_ratio": 0.5,
    "degraded_to_human": True,
}

FAIL_ERROR_TRACE = {
    "trace_id": "t-fail-2",
    "timestamp": "2026-07-19T10:10:00Z",
    "skill": "gcp-gce-ops",
    "op": "DeleteInstance",
    "result": "ERROR",
    "error_type": "TIMEOUT",
    "safety_score": 1.0,
    "autonomy_ratio": 0.8,
}

OTHER_SKILL_FAIL = {
    "trace_id": "t-fail-3",
    "timestamp": "2026-07-19T10:15:00Z",
    "skill": "gcp-iam-ops",
    "op": "SetPolicy",
    "result": "MAX_ITER",
    "safety_score": 1.0,
    "autonomy_ratio": 0.3,
}


class TestScanTraces:
    """Verify trace directory scanning and filtering."""

    def test_scans_gcl_trace_files(self, tmp_path: Path) -> None:
        _write_trace(tmp_path, "gcl-trace-1.json", PASS_TRACE)
        _write_trace(tmp_path, "gcl-trace-2.json", FAIL_SAFETY_TRACE)
        # Non-matching file should be ignored
        _write_trace(tmp_path, "other.json", PASS_TRACE)

        traces = scan_traces(tmp_path)
        assert len(traces) == 2

    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        traces = scan_traces(tmp_path / "does-not-exist")
        assert traces == []

    def test_skips_malformed_trace(self, tmp_path: Path) -> None:
        _write_trace(tmp_path, "gcl-trace-bad.json", {"no_skill": True})
        _write_trace(tmp_path, "gcl-trace-garbage.json", "not json at all")
        traces = scan_traces(tmp_path)
        assert traces == []


class TestAggregate:
    """Verify per-skill aggregation and failure detection."""

    def test_aggregates_by_skill(self) -> None:
        by_skill = aggregate([PASS_TRACE, FAIL_SAFETY_TRACE, FAIL_ERROR_TRACE, OTHER_SKILL_FAIL])
        assert set(by_skill) == {"gcp-gce-ops", "gcp-iam-ops"}

    def test_counts_failures(self) -> None:
        by_skill = aggregate([PASS_TRACE, FAIL_SAFETY_TRACE, FAIL_ERROR_TRACE])
        q = by_skill["gcp-gce-ops"]
        assert q.total == 3
        assert q.failures == 2
        assert q.pass_rate == pytest.approx(1 / 3)

    def test_failure_dimensions(self) -> None:
        by_skill = aggregate([FAIL_SAFETY_TRACE, FAIL_ERROR_TRACE])
        q = by_skill["gcp-gce-ops"]
        assert q.result_counts["SAFETY_FAIL"] == 1
        assert q.result_counts["ERROR"] == 1
        assert q.error_types["PERMISSION_DENIED"] == 1
        assert q.error_types["TIMEOUT"] == 1
        assert q.degraded_count == 1
        assert q.low_safety_count == 1
        assert q.low_autonomy_count == 2
        assert q.failure_ops["DeleteInstance"] == 2

    def test_pass_only_skill(self) -> None:
        by_skill = aggregate([PASS_TRACE])
        q = by_skill["gcp-gce-ops"]
        assert q.failures == 0
        assert q.degraded_count == 0
        assert q.low_safety_count == 0


class TestBuildReport:
    """Verify report rendering."""

    def test_report_includes_skill_and_failures(self) -> None:
        by_skill = aggregate([PASS_TRACE, FAIL_SAFETY_TRACE, FAIL_ERROR_TRACE, OTHER_SKILL_FAIL])
        report = build_report(by_skill)
        assert "# GCL Skill Quality Report" in report
        assert "gcp-gce-ops" in report
        assert "gcp-iam-ops" in report
        assert "SAFETY_FAIL" in report
        assert "PERMISSION_DENIED" in report

    def test_report_empty(self) -> None:
        report = build_report({})
        assert "No traces found" in report


class TestMain:
    """End-to-end CLI behavior."""

    def test_main_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _write_trace(tmp_path, "gcl-trace-1.json", PASS_TRACE)
        _write_trace(tmp_path, "gcl-trace-2.json", FAIL_SAFETY_TRACE)
        rc = main(["--trace-dir", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "gcp-gce-ops" in out
        assert "SAFETY_FAIL" in out

    def test_main_report_path(self, tmp_path: Path) -> None:
        _write_trace(tmp_path, "gcl-trace-1.json", FAIL_ERROR_TRACE)
        report_file = tmp_path / "report.md"
        rc = main(["--trace-dir", str(tmp_path), "--report-path", str(report_file)])
        assert rc == 0
        assert report_file.exists()
        content = report_file.read_text()
        assert "gcp-gce-ops" in content
        assert "TIMEOUT" in content

    def test_main_missing_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        rc = main(["--trace-dir", str(tmp_path / "nope")])
        assert rc == 0  # empty scan is not an error
        assert "No traces found" in capsys.readouterr().out


class TestParseArgs:
    """CLI argument parsing boundaries."""

    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.trace_dir == "./audit-results"
        assert args.report_path is None

    def test_trace_dir_override(self, tmp_path: Path) -> None:
        args = parse_args(["--trace-dir", str(tmp_path)])
        assert args.trace_dir == str(tmp_path)

    def test_report_path_override(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        args = parse_args(["--report-path", str(target)])
        assert args.report_path == str(target)

    def test_both_overrides(self, tmp_path: Path) -> None:
        d = tmp_path / "traces"
        p = tmp_path / "report.md"
        args = parse_args(["--trace-dir", str(d), "--report-path", str(p)])
        assert args.trace_dir == str(d)
        assert args.report_path == str(p)

    def test_unknown_arg_exits(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--no-such-flag"])

