"""
GCL Enhanced Trace Schema Definition.

This module defines the BigQuery-ready GCL trace schema for observability.
Version: 1.0.0
Updated: 2026-07-18
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class GCLResult(str, Enum):
    """Valid GCL execution results."""
    PASS = "PASS"
    MAX_ITER = "MAX_ITER"
    SAFETY_FAIL = "SAFETY_FAIL"
    ERROR = "ERROR"


class GCPErrorType(str, Enum):
    """Valid GCP error types."""
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNAVAILABLE = "UNAVAILABLE"


class Environment(str, Enum):
    """Valid environments."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


@dataclass
class AutonomyDecision:
    """Represents a single autonomous decision made during GCL execution."""
    type: str  # AUTO_RETRY | AUTO_APPROVE | AUTO_REJECT | DEGRADE_TO_HUMAN
    reason: str
    timestamp: str  # ISO 8601
    approved: bool


@dataclass
class IterationTrace:
    """Represents a single GCL iteration."""
    iteration: int
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    critique: dict[str, Any] = field(default_factory=dict)
    verdict: str = ""  # PASS | CONTINUE | SAFETY_FAIL | MAX_ITER


@dataclass
class GCLTrace:
    """
    GCL Enhanced Trace Schema for BigQuery.

    This schema captures all relevant metrics for Level 3 observability:
    - Execution metrics (latency, iterations, exit code)
    - Safety scoring
    - Autonomy decisions
    - Error classification
    """

    # Trace identification
    trace_id: str
    timestamp: str  # ISO 8601 format

    # Operation context
    skill: str
    op: str
    user_request: str = ""

    # Execution result
    result: GCLResult = GCLResult.PASS
    exit_code: int = 0

    # Performance metrics
    latency_ms: int = 0
    iterations_count: int = 0
    autonomy_ratio: float = 0.0  # 0.0 - 1.0

    # Safety scoring
    safety_score: float = 1.0  # 0.0 - 1.0
    safety_failures: int = 0

    # Error classification
    error_type: GCPErrorType | None = None

    # Decision tracking
    autonomy_decisions: list[AutonomyDecision] = field(default_factory=list)
    degraded_to_human: bool = False
    degradation_reason: str | None = None

    # Iteration details
    iterations: list[IterationTrace] = field(default_factory=list)

    # GCP context
    gcp_project: str | None = None
    gcp_region: str | None = None

    # Environment
    environment: Environment = Environment.PRODUCTION

    # Metadata
    trace_version: str = "1.0.0"
    runner_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        # Convert enums to values
        d["result"] = self.result.value if isinstance(self.result, Enum) else self.result
        d["error_type"] = self.error_type.value if self.error_type else None
        d["environment"] = self.environment.value if isinstance(self.environment, Enum) else self.environment
        # Convert iteration objects
        d["iterations"] = [i.__dict__ if hasattr(i, '__dict__') else i for i in self.iterations]
        d["autonomy_decisions"] = [a.__dict__ if hasattr(a, '__dict__') else a for a in self.autonomy_decisions]
        return d

    def validate(self) -> list[str]:
        """Validate the trace. Returns list of errors."""
        errors = []

        # Required fields
        if not self.trace_id:
            errors.append("trace_id is required")
        if not self.timestamp:
            errors.append("timestamp is required")
        if not self.skill:
            errors.append("skill is required")
        if not self.op:
            errors.append("op is required")

        # Range checks
        if not 0.0 <= self.autonomy_ratio <= 1.0:
            errors.append(f"autonomy_ratio out of range: {self.autonomy_ratio}")
        if not 0.0 <= self.safety_score <= 1.0:
            errors.append(f"safety_score out of range: {self.safety_score}")
        if self.latency_ms < 0:
            errors.append(f"latency_ms negative: {self.latency_ms}")

        # Result validation
        valid_results = {e.value for e in GCLResult}
        if self.result not in valid_results:
            errors.append(f"Invalid result: {self.result}")

        # Error type validation
        if self.error_type:
            valid_errors = {e.value for e in GCPErrorType}
            if self.error_type not in valid_errors:
                errors.append(f"Invalid error_type: {self.error_type}")

        # Environment validation
        valid_envs = {e.value for e in Environment}
        if self.environment not in valid_envs:
            errors.append(f"Invalid environment: {self.environment}")

        return errors


# BigQuery schema as Python dict for programmatic use
BIGQUERY_SCHEMA = [
    {"name": "trace_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "skill", "type": "STRING", "mode": "REQUIRED"},
    {"name": "op", "type": "STRING", "mode": "REQUIRED"},
    {"name": "user_request", "type": "STRING", "mode": "NULLABLE"},
    {"name": "result", "type": "STRING", "mode": "REQUIRED"},
    {"name": "exit_code", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "latency_ms", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "iterations_count", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "autonomy_ratio", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "safety_score", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "safety_failures", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "error_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "autonomy_decisions", "type": "JSON", "mode": "NULLABLE"},
    {"name": "degraded_to_human", "type": "BOOLEAN", "mode": "NULLABLE"},
    {"name": "degradation_reason", "type": "STRING", "mode": "NULLABLE"},
    {"name": "iterations", "type": "JSON", "mode": "NULLABLE"},
    {"name": "gcp_project", "type": "STRING", "mode": "NULLABLE"},
    {"name": "gcp_region", "type": "STRING", "mode": "NULLABLE"},
    {"name": "environment", "type": "STRING", "mode": "NULLABLE"},
    {"name": "trace_version", "type": "STRING", "mode": "NULLABLE"},
    {"name": "runner_version", "type": "STRING", "mode": "NULLABLE"},
]
