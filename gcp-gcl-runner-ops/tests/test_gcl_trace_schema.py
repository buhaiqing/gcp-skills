#!/usr/bin/env python3
"""
Tests for GCL Enhanced Trace Schema.

These tests define the expected schema for BigQuery-ready GCL traces.
Run with: python -m pytest tests/test_gcl_trace_schema.py -v
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

# ── Expected Schema Definition ──────────────────────────────────────────────

EXPECTED_TRACE_FIELDS = {
    # Trace identification
    "trace_id": str,
    "timestamp": str,  # ISO 8601 format

    # Operation context
    "skill": str,
    "op": str,
    "user_request": str,

    # Execution result
    "result": str,  # PASS | MAX_ITER | SAFETY_FAIL | ERROR
    "exit_code": int,

    # Performance metrics
    "latency_ms": int,  # Total execution time in milliseconds
    "iterations_count": int,
    "autonomy_ratio": float,  # 0.0 - 1.0

    # Safety scoring
    "safety_score": float,  # 0.0 - 1.0
    "safety_failures": int,  # Number of safety checks that failed

    # Error classification
    "error_type": str | None,  # INVALID_ARGUMENT | PERMISSION_DENIED | NOT_FOUND | TIMEOUT | INTERNAL | None

    # Decision tracking
    "autonomy_decisions": list[dict],  # List of autonomous decisions made
    "degraded_to_human": bool,  # True if human intervention was required
    "degradation_reason": str | None,

    # Iteration details
    "iterations": list[dict],

    # GCP context
    "gcp_project": str | None,
    "gcp_region": str | None,

    # Environment
    "environment": str,  # production | staging | development
}


class TestGCLTraceSchema:
    """Test suite for GCL Enhanced Trace Schema validation."""

    def test_trace_has_all_required_fields(self, sample_trace: dict[str, Any]) -> None:
        """Verify trace contains all required fields."""
        for field, expected_type in EXPECTED_TRACE_FIELDS.items():
            assert field in sample_trace, f"Missing required field: {field}"

    def test_trace_id_format(self, sample_trace: dict[str, Any]) -> None:
        """Verify trace_id follows expected format: gcl-trace-YYYYMMDD-HHMMSS-xxxxxx."""
        import re
        trace_id = sample_trace["trace_id"]
        pattern = r"^gcl-trace-\d{8}-\d{6}-[a-z0-9]{6}$"
        assert re.match(pattern, trace_id), f"Invalid trace_id format: {trace_id}"

    def test_timestamp_is_iso8601(self, sample_trace: dict[str, Any]) -> None:
        """Verify timestamp is valid ISO 8601 format."""
        ts = sample_trace["timestamp"]
        # Should not raise if valid
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_result_is_valid_enum(self, sample_trace: dict[str, Any]) -> None:
        """Verify result is one of valid values."""
        valid_results = {"PASS", "MAX_ITER", "SAFETY_FAIL", "ERROR"}
        assert sample_trace["result"] in valid_results, f"Invalid result: {sample_trace['result']}"

    def test_safety_score_in_range(self, sample_trace: dict[str, Any]) -> None:
        """Verify safety_score is between 0.0 and 1.0."""
        score = sample_trace["safety_score"]
        assert 0.0 <= score <= 1.0, f"safety_score out of range: {score}"

    def test_autonomy_ratio_in_range(self, sample_trace: dict[str, Any]) -> None:
        """Verify autonomy_ratio is between 0.0 and 1.0."""
        ratio = sample_trace["autonomy_ratio"]
        assert 0.0 <= ratio <= 1.0, f"autonomy_ratio out of range: {ratio}"

    def test_error_type_is_valid_or_none(self, sample_trace: dict[str, Any]) -> None:
        """Verify error_type is valid GCP error code or None."""
        error_type = sample_trace["error_type"]
        valid_errors = {
            "INVALID_ARGUMENT",
            "PERMISSION_DENIED",
            "NOT_FOUND",
            "TIMEOUT",
            "INTERNAL",
            "UNAUTHENTICATED",
            "RESOURCE_EXHAUSTED",
            "FAILED_PRECONDITION",
            "ABORTED",
            "OUT_OF_RANGE",
            "UNAVAILABLE",
            None,
        }
        assert error_type in valid_errors, f"Invalid error_type: {error_type}"

    def test_iterations_is_list(self, sample_trace: dict[str, Any]) -> None:
        """Verify iterations is a list."""
        assert isinstance(sample_trace["iterations"], list)

    def test_iterations_count_matches(self, sample_trace: dict[str, Any]) -> None:
        """Verify iterations_count matches actual iterations length."""
        assert sample_trace["iterations_count"] == len(sample_trace["iterations"])

    def test_autonomy_decisions_structure(self, sample_trace: dict[str, Any]) -> None:
        """Verify each autonomy decision has required fields."""
        for decision in sample_trace["autonomy_decisions"]:
            assert "type" in decision, "autonomy_decision missing 'type'"
            assert "reason" in decision, "autonomy_decision missing 'reason'"
            assert "timestamp" in decision, "autonomy_decision missing 'timestamp'"
            assert "approved" in decision, "autonomy_decision missing 'approved'"

    def test_latency_ms_is_positive(self, sample_trace: dict[str, Any]) -> None:
        """Verify latency_ms is non-negative."""
        assert sample_trace["latency_ms"] >= 0, f"latency_ms negative: {sample_trace['latency_ms']}"

    def test_environment_is_valid(self, sample_trace: dict[str, Any]) -> None:
        """Verify environment is valid."""
        valid_envs = {"production", "staging", "development"}
        assert sample_trace["environment"] in valid_envs, f"Invalid environment: {sample_trace['environment']}"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_trace() -> dict[str, Any]:
    """Sample trace for testing."""
    return {
        "trace_id": "gcl-trace-20260718-143052-abc123",
        "timestamp": "2026-07-18T14:30:52+00:00",
        "skill": "gcp-gce-ops",
        "op": "DeleteInstance",
        "user_request": "Delete the instance dev-server-01 in zone us-central1-a",
        "result": "PASS",
        "exit_code": 0,
        "latency_ms": 4523,
        "iterations_count": 2,
        "autonomy_ratio": 0.75,
        "safety_score": 1.0,
        "safety_failures": 0,
        "error_type": None,
        "autonomy_decisions": [
            {
                "type": "AUTO_RETRY",
                "reason": "First attempt failed with TRANSIENT_ERROR",
                "timestamp": "2026-07-18T14:30:53+00:00",
                "approved": True,
            }
        ],
        "degraded_to_human": False,
        "degradation_reason": None,
        "iterations": [
            {
                "iteration": 0,
                "command": "gcloud compute instances delete dev-server-01 --zone=us-central1-a --quiet",
                "exit_code": -1,
                "stdout": "",
                "stderr": "ERROR: (gcloud.compute.instances.delete) PERMISSION_DENIED",
                "critique": {
                    "correctness": 0.0,
                    "safety": 1.0,
                    "idempotency": 0.0,
                    "traceability": 0.8,
                    "spec_compliance": 0.8,
                    "highest_risk": "ERROR",
                },
                "verdict": "CONTINUE",
            },
            {
                "iteration": 1,
                "command": "gcloud compute instances delete dev-server-01 --zone=us-central1-a --quiet",
                "exit_code": 0,
                "stdout": "Deleted instance.",
                "stderr": "",
                "critique": {
                    "correctness": 1.0,
                    "safety": 1.0,
                    "idempotency": 0.8,
                    "traceability": 0.8,
                    "spec_compliance": 0.8,
                    "highest_risk": "INFO",
                },
                "verdict": "PASS",
            },
        ],
        "gcp_project": "my-project-123",
        "gcp_region": "us-central1",
        "environment": "production",
    }


# ── Schema Validation ──────────────────────────────────────────────────────────

def validate_trace_schema(trace: dict[str, Any]) -> list[str]:
    """Validate a trace against the expected schema. Returns list of errors."""
    errors = []

    for field, expected_type in EXPECTED_TRACE_FIELDS.items():
        if field not in trace:
            errors.append(f"Missing required field: {field}")
            continue

        # Type checking for basic types
        if expected_type in (str, int, float, bool, list, dict):
            if not isinstance(trace[field], expected_type):
                errors.append(f"Field '{field}' has wrong type: expected {expected_type}, got {type(trace[field])}")

    return errors
