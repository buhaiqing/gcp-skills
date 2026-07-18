#!/usr/bin/env python3
"""
GCL Structured Logging for Cloud Logging Integration.

This module provides structured logging for the Generator-Critic-Loop (GCL)
adversarial quality gate, with Cloud Logging (GCP) handler support.

Usage:
    from gcl_logging import get_gcl_logger

    logger = get_gcl_logger("gcl-runner")
    logger.info("GCL iteration completed", extra={"result": "PASS", "latency_ms": 1234})
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ── Optional Cloud Logging import ────────────────────────────────────────────

try:
    from google.cloud import logging_v2
    from google.cloud.logging_v2.handlers import CloudLoggingHandler
    from google.cloud.logging_v2.resource import Resource

    _CLOUD_LOGGING_AVAILABLE = True
except ImportError:
    _CLOUD_LOGGING_AVAILABLE = False


# ── Error Classification ─────────────────────────────────────────────────────


class GCLErrorType(Enum):
    """GCP error types for classification."""

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
    UNKNOWN = "UNKNOWN"


class GCLResult(Enum):
    """GCL operation results."""

    PASS = "PASS"
    FAIL = "FAIL"
    MAX_ITER = "MAX_ITER"
    SAFETY_FAIL = "SAFETY_FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


# ── Structured Log Entry ─────────────────────────────────────────────────────


@dataclass
class GCLLogEntry:
    """Structured log entry for GCL events."""

    timestamp: str
    severity: str
    logger: str
    message: str
    trace_id: str
    skill: str
    op: str
    result: str
    latency_ms: int
    autonomy_ratio: float
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# ── JSON Formatter ───────────────────────────────────────────────────────────


class GCLJsonFormatter(logging.Formatter):
    """JSON formatter for structured GCL logging."""

    def __init__(self, *, include_extra: bool = True) -> None:
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        entry = GCLLogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            severity=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            trace_id=getattr(record, "trace_id", _get_or_create_trace_id()),
            skill=getattr(record, "skill", ""),
            op=getattr(record, "op", ""),
            result=getattr(record, "result", ""),
            latency_ms=getattr(record, "latency_ms", 0),
            autonomy_ratio=getattr(record, "autonomy_ratio", 0.0),
            extra=getattr(record, "extra", {}) if self.include_extra else {},
        )

        log_dict = entry.to_dict()

        # Merge extra fields at top level for Cloud Logging compatibility
        if self.include_extra and entry.extra:
            for key, value in entry.extra.items():
                if key not in log_dict:
                    log_dict[key] = value

        return json.dumps(log_dict, default=str)


# ── Trace ID Management ──────────────────────────────────────────────────────


_trace_id: str | None = None


def _get_or_create_trace_id() -> str:
    """Get or create a trace ID for the current GCL run."""
    global _trace_id
    if _trace_id is None:
        _trace_id = f"gcl-trace-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    return _trace_id


def reset_trace_id() -> None:
    """Reset the trace ID (for testing or new GCL runs)."""
    global _trace_id
    _trace_id = None


def set_trace_id(trace_id: str) -> None:
    """Set a specific trace ID."""
    global _trace_id
    _trace_id = trace_id


# ── Error Classification Helpers ─────────────────────────────────────────────


def classify_gcp_error(error_message: str) -> GCLErrorType:
    """Classify a GCP error from error message or stderr output."""
    msg_upper = error_message.upper()

    error_mappings = {
        GCLErrorType.INVALID_ARGUMENT: [
            "INVALID_ARGUMENT",
            "invalid argument",
            "bad request",
            "400",
        ],
        GCLErrorType.PERMISSION_DENIED: [
            "PERMISSION_DENIED",
            "permission denied",
            "403",
            "access denied",
            "not authorized",
        ],
        GCLErrorType.NOT_FOUND: [
            "NOT_FOUND",
            "not found",
            "404",
            "does not exist",
            "no such file",
        ],
        GCLErrorType.TIMEOUT: [
            "TIMEOUT",
            "timeout",
            "deadline exceeded",
            "timed out",
            "504",
        ],
        GCLErrorType.INTERNAL: [
            "INTERNAL",
            "internal error",
            "500",
            "internal server error",
        ],
        GCLErrorType.UNAUTHENTICATED: [
            "UNAUTHENTICATED",
            "unauthenticated",
            "401",
            "unauthorized",
            "not authenticated",
        ],
        GCLErrorType.RESOURCE_EXHAUSTED: [
            "RESOURCE_EXHAUSTED",
            "resource exhausted",
            "quota",
            "429",
            "rate limit",
        ],
        GCLErrorType.FAILED_PRECONDITION: [
            "FAILED_PRECONDITION",
            "failed precondition",
            "precondition failed",
        ],
        GCLErrorType.ABORTED: [
            "ABORTED",
            "aborted",
            "409",
            "conflict",
        ],
        GCLErrorType.OUT_OF_RANGE: [
            "OUT_OF_RANGE",
            "out of range",
            "400",
        ],
        GCLErrorType.UNAVAILABLE: [
            "UNAVAILABLE",
            "unavailable",
            "503",
            "service unavailable",
        ],
    }

    for error_type, patterns in error_mappings.items():
        for pattern in patterns:
            if pattern in msg_upper:
                return error_type

    return GCLErrorType.UNKNOWN


def classify_result(exit_code: int, stderr: str = "", error_type: GCLErrorType | None = None) -> GCLResult:
    """Classify GCL operation result from exit code and error information."""
    if exit_code == 0:
        return GCLResult.PASS

    if error_type == GCLErrorType.PERMISSION_DENIED:
        return GCLResult.SAFETY_FAIL

    if "timeout" in stderr.lower() or error_type == GCLErrorType.TIMEOUT:
        return GCLResult.ERROR

    if exit_code < 0:
        return GCLResult.ERROR

    return GCLResult.FAIL


# ── Logger Factory ───────────────────────────────────────────────────────────


def get_gcl_logger(
    name: str,
    level: int = logging.INFO,
    *,
    use_cloud_logging: bool = True,
    project_id: str | None = None,
    resource_type: str = "gcp_skills_gcl",
    resource_labels: dict[str, str] | None = None,
) -> logging.Logger:
    """
    Get a structured GCL logger with Cloud Logging integration.

    Args:
        name: Logger name (e.g., "gcl-runner", "gcl-generator", "gcl-critic")
        level: Logging level (default: INFO)
        use_cloud_logging: Whether to add Cloud Logging handler (default: True)
        project_id: GCP project ID (default: from CLOUDSDK_CORE_PROJECT env)
        resource_type: Resource type for Cloud Logging (default: "gcp_skills_gcl")
        resource_labels: Resource labels for Cloud Logging

    Returns:
        Configured logger instance

    Example:
        logger = get_gcl_logger("gcl-runner")
        logger.info("GCL iteration completed",
            extra={
                "result": "PASS",
                "latency_ms": 1234,
                "autonomy_ratio": 0.75,
                "skill": "gcp-gce-ops",
                "op": "DeleteInstance",
            })
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # JSON formatter for structured output
    json_formatter = GCLJsonFormatter(include_extra=True)

    # Only add console handler if no handler with our formatter exists
    # This allows pytest caplog to work properly
    has_gcl_handler = any(
        isinstance(h, logging.StreamHandler) and isinstance(h.formatter, GCLJsonFormatter)
        for h in logger.handlers
    )
    if not has_gcl_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)

    # Cloud Logging handler (GCP)
    if use_cloud_logging and _CLOUD_LOGGING_AVAILABLE:
        try:
            gcp_project = project_id or os.environ.get("CLOUDSDK_CORE_PROJECT", "")

            if gcp_project:
                # Create Cloud Logging client
                client = logging_v2.Client(project=gcp_project)

                # Build resource descriptor
                resource = Resource(
                    type=resource_type,
                    labels=resource_labels or {
                        "project_id": gcp_project,
                        "environment": os.environ.get("GCP_SKILLS_ENV", "development"),
                    },
                )

                # Create Cloud Logging handler
                cloud_handler = CloudLoggingHandler(
                    client,
                    resource=resource,
                    labels={
                        "application": "gcp-skills",
                        "component": name,
                    },
                )
                cloud_handler.setLevel(level)
                cloud_handler.setFormatter(json_formatter)
                logger.addHandler(cloud_handler)
                logger.info(f"Cloud Logging enabled for logger '{name}' in project '{gcp_project}'")
            else:
                logger.warning("CLOUDSDK_CORE_PROJECT not set, skipping Cloud Logging handler")
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Logging handler: {e}")

    # Note: propagate=True (default) so pytest caplog can capture records
    # Avoid duplicate output by ensuring only one handler outputs to stderr

    return logger


# ── Convenience Functions ────────────────────────────────────────────────────


def log_gcl_event(
    logger: logging.Logger,
    message: str,
    severity: str = "INFO",
    *,
    skill: str = "",
    op: str = "",
    result: str = "",
    latency_ms: int = 0,
    autonomy_ratio: float = 0.0,
    **extra: Any,
) -> None:
    """
    Log a GCL event with structured fields.

    Args:
        logger: Logger instance from get_gcl_logger()
        message: Log message
        severity: Log level (INFO, WARNING, ERROR, etc.)
        skill: Skill name (e.g., "gcp-gce-ops")
        op: Operation name (e.g., "DeleteInstance")
        result: GCL result (PASS, FAIL, MAX_ITER, etc.)
        latency_ms: Operation latency in milliseconds
        autonomy_ratio: Autonomy ratio (0.0 - 1.0)
        **extra: Additional fields to include in log entry
    """
    trace_id = _get_or_create_trace_id()

    extra_fields = {
        "trace_id": trace_id,
        "skill": skill,
        "op": op,
        "result": result,
        "latency_ms": latency_ms,
        "autonomy_ratio": autonomy_ratio,
        **extra,
    }

    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, message, extra=extra_fields)


# ── Module Exports ───────────────────────────────────────────────────────────

__all__ = [
    "get_gcl_logger",
    "log_gcl_event",
    "GCLJsonFormatter",
    "GCLLogEntry",
    "GCLErrorType",
    "GCLResult",
    "classify_gcp_error",
    "classify_result",
    "reset_trace_id",
    "set_trace_id",
]
