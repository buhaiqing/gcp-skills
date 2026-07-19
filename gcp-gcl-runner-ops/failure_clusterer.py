"""Failure-pattern clustering over GCL trajectory classifications."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from trajectory_classifier import Classification, TraceClass, classify_directory

# Map known reason prefixes to friendly cluster labels.
_LABEL_MAP: dict[str, str] = {
    "latency_ms": "High latency",
    "iterations_count": "Excessive iterations",
    "autonomy_ratio": "Low autonomy",
    "degraded_to_human": "Degraded to human",
    "exit_code": "Non-zero exit",
    "result=SAFETY_FAIL": "Safety failure",
    "safety_score": "Safety failure",
    "safety_failures": "Safety failure",
    "result=MAX_ITER": "Max iterations reached",
    "result=ERROR": "Execution error",
    "error_type": "GCP error",
}


@dataclass
class Cluster:
    label: str
    signature: str
    category: TraceClass
    count: int = 0
    members: list[str] = field(default_factory=list)


def _signature(reason: str) -> str:
    """Normalize a reason into a stable cluster key.

    Drop "=N" value assignments, collapse remaining digit runs to THRESHOLD,
    and remove spaces ("latency_ms=120000 > 60000" -> "latency_ms>THRESHOLD").
    Categorical reasons (result=SAFETY_FAIL, degraded_to_human=True) stay intact.
    """
    s = re.sub(r"=\d+", "", reason)
    s = re.sub(r"\d+", "THRESHOLD", s)
    return s.replace(" ", "")


def _label_for(reason: str) -> str:
    """Pick a friendly label by prefix match, else raw reason."""
    for prefix, label in _LABEL_MAP.items():
        if reason.startswith(prefix):
            return label
    return reason


def cluster_failures(classifications: list[Classification]) -> list[Cluster]:
    """Group non-SUCCESS classifications into readable clusters by signature. Sorted by count DESC."""
    clusters: dict[str, Cluster] = {}
    for c in classifications:
        if c.category == TraceClass.SUCCESS:
            continue
        key = _signature(c.reason)
        if key not in clusters:
            clusters[key] = Cluster(
                label=_label_for(c.reason), signature=key, category=c.category
            )
        cluster = clusters[key]
        cluster.count += 1
        cluster.members.append(c.trace_id)
    return sorted(clusters.values(), key=lambda cl: cl.count, reverse=True)


def cluster_traces(path: str | Path = "audit-results") -> list[Cluster]:
    """classify_directory(path) then cluster_failures over the result."""
    return cluster_failures(classify_directory(path))
