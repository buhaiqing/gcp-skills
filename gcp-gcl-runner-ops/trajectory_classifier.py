"""Trajectory auto-classification: SUCCESS / FAILURE / ANOMALY."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from gcl_trace_schema import Environment, GCLResult, GCLTrace

logger = logging.getLogger(__name__)


class TraceClass(str, Enum):
    """Classification outcome for a GCL trace."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ANOMALY = "ANOMALY"


@dataclass
class Classification:
    """Result of classifying a single trace."""

    trace_id: str
    category: TraceClass
    reason: str
    source_file: str | None = None


# Threshold constants for anomaly detection.
LATENCY_ANOMALY_MS = 60000
ITER_ANOMALY_COUNT = 5
AUTONOMY_ANOMALY_MIN = 0.5


def _coerce_enums(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce persisted enum string fields back into their Enum types."""
    if "result" in data and data["result"] is not None:
        data["result"] = GCLResult(data["result"])
    if "environment" in data and data["environment"] is not None:
        data["environment"] = Environment(data["environment"])
    if "error_type" in data and data["error_type"] is not None:
        # GCPErrorType shares value space with GCLTrace.error_type string.
        from gcl_trace_schema import GCPErrorType

        data["error_type"] = GCPErrorType(data["error_type"])
    return data


def classify_trace(trace: GCLTrace) -> Classification:
    """Classify a single GCLTrace. First matching rule wins (priority order)."""
    # 1. Hard failure: safety violation.
    if (
        trace.result == GCLResult.SAFETY_FAIL
        or trace.safety_score == 0.0
        or trace.safety_failures > 0
    ):
        if trace.result == GCLResult.SAFETY_FAIL:
            reason = "result=SAFETY_FAIL"
        elif trace.safety_score == 0.0:
            reason = f"safety_score={trace.safety_score}"
        else:
            reason = f"safety_failures={trace.safety_failures}"
        return Classification(
            trace_id=trace.trace_id, category=TraceClass.FAILURE, reason=reason
        )

    # 2. Failure: max iterations / error / non-zero exit.
    if (
        trace.result in (GCLResult.MAX_ITER, GCLResult.ERROR)
        or trace.exit_code != 0
    ):
        if trace.exit_code != 0:
            reason = f"exit_code={trace.exit_code}"
        elif trace.result == GCLResult.MAX_ITER:
            reason = "result=MAX_ITER (reached max iterations)"
        else:
            reason = f"result={trace.result.value}"
        return Classification(
            trace_id=trace.trace_id, category=TraceClass.FAILURE, reason=reason
        )

    # 3. Anomaly: soft signals indicating degraded execution.
    if trace.degraded_to_human:
        return Classification(
            trace_id=trace.trace_id,
            category=TraceClass.ANOMALY,
            reason="degraded_to_human=True",
        )
    if trace.latency_ms > LATENCY_ANOMALY_MS:
        return Classification(
            trace_id=trace.trace_id,
            category=TraceClass.ANOMALY,
            reason=f"latency_ms={trace.latency_ms} > {LATENCY_ANOMALY_MS}",
        )
    if trace.iterations_count >= ITER_ANOMALY_COUNT:
        return Classification(
            trace_id=trace.trace_id,
            category=TraceClass.ANOMALY,
            reason=f"iterations_count={trace.iterations_count} >= {ITER_ANOMALY_COUNT}",
        )
    if trace.autonomy_ratio < AUTONOMY_ANOMALY_MIN:
        return Classification(
            trace_id=trace.trace_id,
            category=TraceClass.ANOMALY,
            reason=f"autonomy_ratio={trace.autonomy_ratio} < {AUTONOMY_ANOMALY_MIN}",
        )
    if trace.error_type is not None:
        error_value = trace.error_type.value if isinstance(trace.error_type, Enum) else trace.error_type
        return Classification(
            trace_id=trace.trace_id,
            category=TraceClass.ANOMALY,
            reason=f"error_type={error_value}",
        )

    # 4. Success.
    return Classification(
        trace_id=trace.trace_id,
        category=TraceClass.SUCCESS,
        reason="all quality gates passed",
    )


def classify_directory(path: str | Path = "audit-results") -> list[Classification]:
    """Classify all gcl-trace-*.json files under path. Missing dir → []."""
    base = Path(path)
    if not base.exists():
        return []

    results: list[Classification] = []
    for file_path in sorted(base.glob("gcl-trace-*.json")):
        try:
            with file_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            data = _coerce_enums(data)
            trace = GCLTrace(**data)
        except (json.JSONDecodeError, FileNotFoundError, TypeError, ValueError) as exc:
            logger.warning("Skipping %s: %s", file_path, exc)
            continue

        classification = classify_trace(trace)
        classification.source_file = file_path.name
        results.append(classification)

    return results
