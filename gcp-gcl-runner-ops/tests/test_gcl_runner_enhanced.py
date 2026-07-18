#!/usr/bin/env python3
"""
Tests for GCL Enhanced Runner retry logic.

Run with: python -m pytest gcp-gcl-runner-ops/tests/test_gcl_runner_enhanced.py -v
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from unittest.mock import patch, MagicMock

import pytest

# Import the module under test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from gcl_runner_enhanced import (
    generate,
    classify_error,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRY_EXPONENTIAL_FACTOR,
    RETRY_MAX_RETRIES,
    RETRYABLE_ERROR_TYPES,
)
from gcl_trace_schema import GCPErrorType


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def reset_trace_id():
    """Reset trace ID before each test."""
    from gcl_logging import reset_trace_id

    reset_trace_id()
    yield
    reset_trace_id()


@pytest.fixture
def logger(caplog: pytest.LogCaptureFixture) -> logging.Logger:
    """Get a test logger with Cloud Logging disabled."""
    from gcl_logging import get_gcl_logger

    return get_gcl_logger("test-gcl-generator", use_cloud_logging=False)


# ── Retry Configuration Tests ─────────────────────────────────────────────────


class TestRetryConstants:
    """Test suite for retry configuration constants."""

    def test_retry_base_delay_is_1_second(self) -> None:
        """Verify base delay is 1 second."""
        assert RETRY_BASE_DELAY == 1.0

    def test_retry_max_delay_is_60_seconds(self) -> None:
        """Verify max delay is 60 seconds."""
        assert RETRY_MAX_DELAY == 60.0

    def test_retry_exponential_factor_is_2x(self) -> None:
        """Verify exponential factor is 2."""
        assert RETRY_EXPONENTIAL_FACTOR == 2.0

    def test_retry_max_retries_is_3(self) -> None:
        """Verify max retries is 3."""
        assert RETRY_MAX_RETRIES == 3

    def test_retryable_error_types_includes_transient_errors(self) -> None:
        """Verify all transient error types are retryable."""
        expected = {
            GCPErrorType.TIMEOUT,
            GCPErrorType.INTERNAL,
            GCPErrorType.UNAVAILABLE,
            GCPErrorType.RESOURCE_EXHAUSTED,
            GCPErrorType.ABORTED,
        }
        assert RETRYABLE_ERROR_TYPES == expected


# ── Retry on Timeout Tests ────────────────────────────────────────────────────


class TestRetryOnTimeout:
    """Test suite for retry behavior on timeout errors."""

    def test_retry_on_timeout(self, caplog: pytest.LogCaptureFixture, reset_trace_id: None) -> None:
        """Verify command is retried when timeout occurs."""
        call_count = 0

        def mock_run_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.TimeoutExpired("cmd", 5)
            # Second call succeeds
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_timeout):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,  # Use short delay for tests
                max_delay=1.0,
                exponential_factor=2.0,
            )

        assert trace["exit_code"] == 0
        assert trace["retry_count"] == 1
        assert "retry" in caplog.text.lower() or "retrying" in caplog.text.lower()

    def test_timeout_retry_uses_exponential_backoff(self, caplog: pytest.LogCaptureFixture, reset_trace_id: None) -> None:
        """Verify exponential backoff timing on timeout."""
        call_times = []

        def mock_run_with_timing(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) == 1:
                raise subprocess.TimeoutExpired("cmd", 5)
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_with_timing):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.2,  # 200ms base
                max_delay=1.0,
                exponential_factor=2.0,
            )

        assert trace["exit_code"] == 0
        assert len(trace["retry_delays"]) == 1
        # First retry delay should be base_delay * factor^0 = 0.2 * 1 = 0.2
        assert abs(trace["retry_delays"][0] - 0.2) < 0.05

    def test_max_retries_respected_on_timeout(self, reset_trace_id: None) -> None:
        """Verify max retries is respected on persistent timeout."""
        call_count = 0

        def mock_run_always_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise subprocess.TimeoutExpired("cmd", 5)

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_always_timeout):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=2,  # Only 2 retries
                base_delay=0.05,
                max_delay=0.1,
                exponential_factor=2.0,
            )

        assert trace["exit_code"] == -1
        assert call_count == 3  # Initial + 2 retries


# ── No Retry on Permanent Failure Tests ──────────────────────────────────────


class TestNoRetryOnPermanentFailure:
    """Test suite verifying no retry on permanent (non-retryable) errors."""

    def test_no_retry_on_permission_denied(self, reset_trace_id: None) -> None:
        """Verify no retry when permission denied (permanent error)."""
        call_count = 0

        def mock_run_permission_denied(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = ""
            result.stderr = "PERMISSION_DENIED: Access denied"
            result.returncode = 1
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_permission_denied):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,
            )

        assert trace["exit_code"] == 1
        assert trace["retry_count"] == 0  # No retries
        assert trace["stderr"] == "PERMISSION_DENIED: Access denied"

    def test_no_retry_on_not_found(self, reset_trace_id: None) -> None:
        """Verify no retry when resource not found (permanent error)."""
        call_count = 0

        def mock_run_not_found(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = ""
            result.stderr = "NOT_FOUND: Resource does not exist"
            result.returncode = 1
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_not_found):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,
            )

        assert trace["exit_code"] == 1
        assert trace["retry_count"] == 0

    def test_no_retry_on_invalid_argument(self, reset_trace_id: None) -> None:
        """Verify no retry when invalid argument (permanent error)."""
        call_count = 0

        def mock_run_invalid_arg(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = ""
            result.stderr = "INVALID_ARGUMENT: Bad request"
            result.returncode = 1
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_invalid_arg):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,
            )

        assert trace["exit_code"] == 1
        assert trace["retry_count"] == 0


# ── Retryable Error Tests ────────────────────────────────────────────────────


class TestRetryableErrors:
    """Test suite for retryable error types."""

    @pytest.mark.parametrize(
        "error_stderr",
        [
            "TIMEOUT: deadline exceeded",
            "INTERNAL: internal server error",
            "UNAVAILABLE: service unavailable",
            "RESOURCE_EXHAUSTED: quota exceeded",
            "ABORTED: operation aborted",
        ],
    )
    def test_retry_on_transient_errors(self, error_stderr: str, reset_trace_id: None) -> None:
        """Verify retry occurs on all transient error types."""
        call_count = 0

        def mock_run_with_transient_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.stdout = ""
                result.stderr = error_stderr
                result.returncode = 1
                return result
            # Second call succeeds
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_with_transient_error):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,
            )

        assert trace["exit_code"] == 0
        assert trace["retry_count"] == 1


# ── Exponential Backoff Timing Tests ────────────────────────────────────────


class TestExponentialBackoffTiming:
    """Test suite for exponential backoff timing."""

    def test_exponential_delay_increases(self, reset_trace_id: None) -> None:
        """Verify delay increases exponentially with attempts."""
        call_count = 0

        def mock_run_always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = ""
            result.stderr = "TIMEOUT: deadline exceeded"
            result.returncode = 1
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_always_fail):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=3,
                base_delay=0.1,
                max_delay=10.0,
                exponential_factor=2.0,
            )

        assert len(trace["retry_delays"]) == 3
        # First delay: 0.1 * 2^0 = 0.1
        assert abs(trace["retry_delays"][0] - 0.1) < 0.02
        # Second delay: 0.1 * 2^1 = 0.2
        assert abs(trace["retry_delays"][1] - 0.2) < 0.02
        # Third delay: 0.1 * 2^2 = 0.4
        assert abs(trace["retry_delays"][2] - 0.4) < 0.02

    def test_delay_capped_at_max_delay(self, reset_trace_id: None) -> None:
        """Verify delay is capped at max_delay."""
        call_count = 0

        def mock_run_always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = ""
            result.stderr = "TIMEOUT: deadline exceeded"
            result.returncode = 1
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_always_fail):
            trace = generate(
                "echo test",
                dry_run=False,
                timeout=300,
                max_retries=5,
                base_delay=1.0,
                max_delay=2.0,  # Cap at 2 seconds
                exponential_factor=2.0,
            )

        # All delays should be capped at 2.0
        for delay in trace["retry_delays"]:
            assert delay <= 2.0
        # First delay: 1.0 * 2^0 = 1.0
        assert abs(trace["retry_delays"][0] - 1.0) < 0.02
        # Second delay: 1.0 * 2^1 = 2.0 (capped)
        assert abs(trace["retry_delays"][1] - 2.0) < 0.02
        # Third delay: 1.0 * 2^2 = 4.0 (capped to 2.0)
        assert abs(trace["retry_delays"][2] - 2.0) < 0.02

    def test_actual_sleep_time_matches_delay(self, reset_trace_id: None) -> None:
        """Verify actual sleep time matches configured delay."""
        call_times = []
        sleep_times = []

        original_sleep = time.sleep

        def mock_sleep(seconds):
            sleep_times.append(seconds)
            # Don't actually sleep in tests

        def mock_run_with_timing(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) <= 3:  # Fail first 3 times
                result = MagicMock()
                result.stdout = ""
                result.stderr = "TIMEOUT: deadline exceeded"
                result.returncode = 1
                return result
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.time.sleep", mock_sleep):
            with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_with_timing):
                trace = generate(
                    "echo test",
                    dry_run=False,
                    timeout=300,
                    max_retries=3,
                    base_delay=0.2,
                    max_delay=1.0,
                    exponential_factor=2.0,
                )

        # Verify sleep was called with expected delays
        assert len(sleep_times) == 3
        assert abs(sleep_times[0] - 0.2) < 0.02  # base * 2^0
        assert abs(sleep_times[1] - 0.4) < 0.02  # base * 2^1
        assert abs(sleep_times[2] - 0.8) < 0.02  # base * 2^2


# ── Dry Run Tests ────────────────────────────────────────────────────────────


class TestDryRun:
    """Test suite for dry run behavior."""

    def test_dry_run_skips_execution(self, reset_trace_id: None) -> None:
        """Verify dry run returns immediately without executing command."""
        with patch("gcl_runner_enhanced.subprocess.run") as mock_run:
            trace = generate("echo test", dry_run=True)

        mock_run.assert_not_called()
        assert trace["exit_code"] == 0
        assert trace["stdout"] == "[DRY-RUN] Command not executed"
        assert trace["retry_count"] == 0


# ── Trace Fields Tests ────────────────────────────────────────────────────────


class TestTraceFields:
    """Test suite for retry-related trace fields."""

    def test_trace_includes_retry_count(self, reset_trace_id: None) -> None:
        """Verify trace includes retry_count field."""
        call_count = 0

        def mock_run_fails_twice(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                result = MagicMock()
                result.stdout = ""
                result.stderr = "TIMEOUT: deadline exceeded"
                result.returncode = 1
                return result
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_fails_twice):
            trace = generate(
                "echo test",
                dry_run=False,
                max_retries=3,
                base_delay=0.01,
            )

        assert "retry_count" in trace
        assert trace["retry_count"] == 2

    def test_trace_includes_retry_delays(self, reset_trace_id: None) -> None:
        """Verify trace includes retry_delays field."""
        call_count = 0

        def mock_run_fails_twice(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                result = MagicMock()
                result.stdout = ""
                result.stderr = "TIMEOUT: deadline exceeded"
                result.returncode = 1
                return result
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_fails_twice):
            trace = generate(
                "echo test",
                dry_run=False,
                max_retries=3,
                base_delay=0.1,
            )

        assert "retry_delays" in trace
        assert len(trace["retry_delays"]) == 2
        assert all(isinstance(d, float) for d in trace["retry_delays"])


# ── Logging Tests ─────────────────────────────────────────────────────────────


class TestRetryLogging:
    """Test suite for retry logging."""

    def test_retry_attempt_logged(self, caplog: pytest.LogCaptureFixture, reset_trace_id: None) -> None:
        """Verify retry attempts are logged."""
        call_count = 0

        def mock_run_fails_once(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.stdout = ""
                result.stderr = "TIMEOUT: deadline exceeded"
                result.returncode = 1
                return result
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_fails_once):
            trace = generate(
                "echo test",
                dry_run=False,
                max_retries=3,
                base_delay=0.01,
                skill="gcp-test-ops",
                op="TestOp",
            )

        assert trace["retry_count"] > 0
        # Check that retry was logged
        assert any("retry" in record.message.lower() for record in caplog.records)

    def test_completion_after_retries_logged(self, caplog: pytest.LogCaptureFixture, reset_trace_id: None) -> None:
        """Verify completion after retries is logged."""
        call_count = 0

        def mock_run_fails_once(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.stdout = ""
                result.stderr = "TIMEOUT: deadline exceeded"
                result.returncode = 1
                return result
            result = MagicMock()
            result.stdout = "success"
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("gcl_runner_enhanced.subprocess.run", side_effect=mock_run_fails_once):
            trace = generate(
                "echo test",
                dry_run=False,
                max_retries=3,
                base_delay=0.01,
                skill="gcp-test-ops",
                op="TestOp",
            )

        # Check that completion was logged
        assert any("completed" in record.message.lower() for record in caplog.records)
