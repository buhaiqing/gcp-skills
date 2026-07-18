#!/usr/bin/env python3
"""
Tests for GCL Structured Logging.

Run with: python -m pytest tests/test_logging.py -v
"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

# Import the logging module under test
from gcl_logging import (
    GCLErrorType,
    GCLJsonFormatter,
    GCLLogEntry,
    GCLResult,
    classify_gcp_error,
    classify_result,
    get_gcl_logger,
    log_gcl_event,
    reset_trace_id,
    set_trace_id,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_trace() -> None:
    """Reset trace ID before each test."""
    reset_trace_id()
    yield
    reset_trace_id()


@pytest.fixture
def logger() -> logging.Logger:
    """Get a test logger with Cloud Logging disabled."""
    return get_gcl_logger("test-gcl", use_cloud_logging=False)


# ── GCLLogEntry Tests ────────────────────────────────────────────────────────


class TestGCLLogEntry:
    """Test suite for GCLLogEntry dataclass."""

    def test_to_dict_returns_all_fields(self) -> None:
        """Verify to_dict returns all expected fields."""
        entry = GCLLogEntry(
            timestamp="2026-07-18T14:30:52+00:00",
            severity="INFO",
            logger="gcl-runner",
            message="Test message",
            trace_id="gcl-trace-20260718-143052-abc123",
            skill="gcp-gce-ops",
            op="DeleteInstance",
            result="PASS",
            latency_ms=1234,
            autonomy_ratio=0.75,
            extra={"custom_field": "value"},
        )

        result = entry.to_dict()

        assert isinstance(result, dict)
        assert result["timestamp"] == "2026-07-18T14:30:52+00:00"
        assert result["severity"] == "INFO"
        assert result["logger"] == "gcl-runner"
        assert result["message"] == "Test message"
        assert result["trace_id"] == "gcl-trace-20260718-143052-abc123"
        assert result["skill"] == "gcp-gce-ops"
        assert result["op"] == "DeleteInstance"
        assert result["result"] == "PASS"
        assert result["latency_ms"] == 1234
        assert result["autonomy_ratio"] == 0.75
        assert result["extra"]["custom_field"] == "value"

    def test_default_extra_is_empty_dict(self) -> None:
        """Verify extra defaults to empty dict."""
        entry = GCLLogEntry(
            timestamp="2026-07-18T14:30:52+00:00",
            severity="INFO",
            logger="gcl-runner",
            message="Test",
            trace_id="trace-123",
            skill="",
            op="",
            result="",
            latency_ms=0,
            autonomy_ratio=0.0,
        )
        assert entry.extra == {}


# ── JSON Formatter Tests ─────────────────────────────────────────────────────


class TestGCLJsonFormatter:
    """Test suite for GCLJsonFormatter."""

    def test_format_produces_valid_json(self, logger: logging.Logger) -> None:
        """Verify formatter outputs valid JSON."""
        formatter = GCLJsonFormatter()
        record = logger.makeRecord(
            name="test-logger",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add required GCL fields
        record.trace_id = "gcl-trace-20260718-143052-abc123"
        record.skill = "gcp-gce-ops"
        record.op = "DeleteInstance"
        record.result = "PASS"
        record.latency_ms = 500
        record.autonomy_ratio = 0.8
        record.extra = {}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test-logger"
        assert parsed["trace_id"] == "gcl-trace-20260718-143052-abc123"
        assert parsed["skill"] == "gcp-gce-ops"
        assert parsed["op"] == "DeleteInstance"
        assert parsed["result"] == "PASS"
        assert parsed["latency_ms"] == 500
        assert parsed["autonomy_ratio"] == 0.8

    def test_format_includes_extra_fields(self, logger: logging.Logger) -> None:
        """Verify extra fields are included in JSON output."""
        formatter = GCLJsonFormatter(include_extra=True)
        record = logger.makeRecord(
            name="test-logger",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.trace_id = "trace-123"
        record.skill = ""
        record.op = ""
        record.result = ""
        record.latency_ms = 0
        record.autonomy_ratio = 0.0
        record.extra = {"custom_key": "custom_value", "iterations": 3}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["custom_key"] == "custom_value"
        assert parsed["iterations"] == 3


# ── Error Classification Tests ───────────────────────────────────────────────


class TestClassifyGcpError:
    """Test suite for GCP error classification."""

    @pytest.mark.parametrize(
        ("error_msg", "expected"),
        [
            ("PERMISSION_DENIED: Access denied", GCLErrorType.PERMISSION_DENIED),
            ("NOT_FOUND: Resource does not exist", GCLErrorType.NOT_FOUND),
            ("INVALID_ARGUMENT: Bad request", GCLErrorType.INVALID_ARGUMENT),
            ("Error 403: permission denied", GCLErrorType.PERMISSION_DENIED),
            ("Error 404: not found", GCLErrorType.NOT_FOUND),
            ("TIMEOUT: deadline exceeded", GCLErrorType.TIMEOUT),
            ("INTERNAL: internal server error", GCLErrorType.INTERNAL),
            ("UNAUTHENTICATED: not authenticated", GCLErrorType.UNAUTHENTICATED),
            ("RESOURCE_EXHAUSTED: quota exceeded", GCLErrorType.RESOURCE_EXHAUSTED),
            ("FAILED_PRECONDITION: precondition failed", GCLErrorType.FAILED_PRECONDITION),
            ("ABORTED: operation aborted", GCLErrorType.ABORTED),
            ("OUT_OF_RANGE: out of range", GCLErrorType.OUT_OF_RANGE),
            ("UNAVAILABLE: service unavailable", GCLErrorType.UNAVAILABLE),
            ("SOME_UNKNOWN_ERROR", GCLErrorType.UNKNOWN),
            ("Everything is fine", GCLErrorType.UNKNOWN),
        ],
    )
    def test_classify_gcp_error(self, error_msg: str, expected: GCLErrorType) -> None:
        """Verify error classification for various GCP errors."""
        result = classify_gcp_error(error_msg)
        assert result == expected


class TestClassifyResult:
    """Test suite for GCL result classification."""

    def test_exit_code_zero_is_pass(self) -> None:
        """Verify exit code 0 returns PASS."""
        assert classify_result(0, "") == GCLResult.PASS

    def test_permission_denied_is_safety_fail(self) -> None:
        """Verify PERMISSION_DENIED returns SAFETY_FAIL."""
        result = classify_result(1, "PERMISSION_DENIED: Access denied", GCLErrorType.PERMISSION_DENIED)
        assert result == GCLResult.SAFETY_FAIL

    def test_timeout_is_error(self) -> None:
        """Verify timeout returns ERROR."""
        result = classify_result(1, "TIMEOUT: deadline exceeded", GCLErrorType.TIMEOUT)
        assert result == GCLResult.ERROR

    def test_negative_exit_code_is_error(self) -> None:
        """Verify negative exit code returns ERROR."""
        assert classify_result(-1, "") == GCLResult.ERROR

    def test_non_zero_without_special_case_is_fail(self) -> None:
        """Verify non-zero exit without special case returns FAIL."""
        assert classify_result(1, "Generic error") == GCLResult.FAIL


# ── Logger Tests ─────────────────────────────────────────────────────────────


class TestGetGclLogger:
    """Test suite for get_gcl_logger function."""

    def test_returns_logger_with_correct_name(self) -> None:
        """Verify returned logger has correct name."""
        logger = get_gcl_logger("test-logger", use_cloud_logging=False)
        assert logger.name == "test-logger"

    def test_logger_has_json_handler(self) -> None:
        """Verify logger has at least one handler."""
        logger = get_gcl_logger("test-logger", use_cloud_logging=False)
        assert len(logger.handlers) >= 1

    def test_logger_propagates_to_root(self) -> None:
        """Verify logger propagates to root for pytest caplog compatibility."""
        logger = get_gcl_logger("test-logger", use_cloud_logging=False)
        assert logger.propagate is True

    def test_logger_default_level_is_info(self) -> None:
        """Verify default log level is INFO."""
        logger = get_gcl_logger("test-logger", use_cloud_logging=False)
        assert logger.level == logging.INFO

    def test_logger_respects_custom_level(self) -> None:
        """Verify custom log level is respected."""
        logger = get_gcl_logger("test-logger", level=logging.DEBUG, use_cloud_logging=False)
        assert logger.level == logging.DEBUG

    def test_cloud_logging_disabled_when_flag_false(self) -> None:
        """Verify Cloud Logging handler is not added when disabled."""
        with patch("gcl_logging._CLOUD_LOGGING_AVAILABLE", True):
            logger = get_gcl_logger("test-logger", use_cloud_logging=False)
            # Should only have console handler
            assert len(logger.handlers) == 1

    def test_cloud_logging_skipped_when_not_available(self) -> None:
        """Verify Cloud Logging is skipped when library not installed."""
        with patch("gcl_logging._CLOUD_LOGGING_AVAILABLE", False):
            logger = get_gcl_logger("test-logger", use_cloud_logging=True)
            # Should only have console handler
            assert len(logger.handlers) == 1


# ── Log GCL Event Tests ──────────────────────────────────────────────────────


class TestLogGclEvent:
    """Test suite for log_gcl_event function."""

    def test_log_gcl_event_includes_all_fields(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify log_gcl_event includes all structured fields in JSON output."""
        logger = get_gcl_logger("test-logger", use_cloud_logging=False)

        with caplog.at_level(logging.INFO):
            log_gcl_event(
                logger,
                "GCL iteration completed",
                severity="INFO",
                skill="gcp-gce-ops",
                op="DeleteInstance",
                result="PASS",
                latency_ms=1234,
                autonomy_ratio=0.75,
                iterations=2,
            )

        # Verify the log was captured
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Verify structured fields are present as attributes
        assert record.skill == "gcp-gce-ops"
        assert record.op == "DeleteInstance"
        assert record.result == "PASS"
        assert record.latency_ms == 1234
        assert record.autonomy_ratio == 0.75


# ── Trace ID Tests ───────────────────────────────────────────────────────────


class TestTraceId:
    """Test suite for trace ID management."""

    def test_reset_trace_id_clears_id(self) -> None:
        """Verify reset_trace_id clears the current trace ID."""
        set_trace_id("custom-trace-123")
        reset_trace_id()
        # After reset, a new trace ID will be generated
        from gcl_logging import _get_or_create_trace_id

        new_id = _get_or_create_trace_id()
        assert new_id.startswith("gcl-trace-")

    def test_set_trace_id_sets_custom_id(self) -> None:
        """Verify set_trace_id sets a custom trace ID."""
        custom_id = "custom-trace-abc123"
        set_trace_id(custom_id)

        from gcl_logging import _get_or_create_trace_id

        assert _get_or_create_trace_id() == custom_id


# ── Integration Tests ────────────────────────────────────────────────────────


class TestLoggerOutputFormat:
    """Integration tests for logger output format."""

    def test_log_output_is_valid_json(self, capsys: pytest.CaptureFixture) -> None:
        """Verify log output is valid JSON when using JSON formatter."""
        logger = get_gcl_logger("test-integration", use_cloud_logging=False)

        log_gcl_event(
            logger,
            "Test event",
            skill="gcp-gce-ops",
            op="DeleteInstance",
            result="PASS",
            latency_ms=100,
            autonomy_ratio=0.5,
        )

        captured = capsys.readouterr()
        output = captured.err  # JSON formatter outputs to stderr

        parsed = json.loads(output)
        assert parsed["message"] == "Test event"
        assert parsed["skill"] == "gcp-gce-ops"
        assert parsed["op"] == "DeleteInstance"
        assert parsed["result"] == "PASS"
