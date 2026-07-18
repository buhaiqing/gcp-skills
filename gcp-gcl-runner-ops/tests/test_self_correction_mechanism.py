#!/usr/bin/env python3
"""
Tests for self-correction mechanism in GCL Runner.

These tests verify the CorrectionFeedbackLoop, StateSnapshot, and
DegradationDetector components.
Run with: python -m pytest tests/test_self_correction_mechanism.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Ensure the gcl-runner-ops directory is in sys.path
GCL_RUNNER_OPS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(GCL_RUNNER_OPS_DIR))

from self_correction import analyze_and_suggest  # noqa: E402
from self_correction_mechanism import (  # noqa: E402
    CorrectionFeedbackLoop,
    DegradationDetector,
    DegradationReport,
    StateSnapshot,
    StateSnapshotData,
)

# ─────────────────────────────────────────────────────────────────────────────
# CorrectionFeedbackLoop Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCorrectionFeedbackLoop:
    """Test suite for CorrectionFeedbackLoop."""

    def test_feedback_loop_records_corrections(self) -> None:
        """Verify corrections are properly recorded."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            loop = CorrectionFeedbackLoop(state_file=state_file)
            suggestion_id = loop.record_correction(
                error_type="timeout",
                suggestion_text="Increase timeout value",
                context={"command": "gcloud compute instances list"},
            )

            assert suggestion_id is not None
            assert len(suggestion_id) > 0

            corrections = loop.all_corrections()
            assert len(corrections) == 1
            assert corrections[0]["error_type"] == "timeout"
            assert corrections[0]["suggestion_text"] == "Increase timeout value"
            assert corrections[0]["context"]["command"] == "gcloud compute instances list"
            assert corrections[0]["applied"] is False
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_feedback_loop_applies_previous_corrections(self) -> None:
        """Verify corrections can be retrieved and marked as applied."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            loop = CorrectionFeedbackLoop(state_file=state_file)
            suggestion_id = loop.record_correction(
                error_type="auth_error",
                suggestion_text="Refresh authentication tokens",
            )

            # Get applicable suggestions
            suggestions = loop.get_applicable_suggestions("auth_error")
            assert len(suggestions) == 1
            assert suggestions[0]["suggestion_id"] == suggestion_id

            # Mark as applied
            result = loop.mark_applied(suggestion_id)
            assert result is True

            # Verify it's marked
            corrections = loop.all_corrections()
            assert corrections[0]["applied"] is True
            assert corrections[0]["applied_count"] == 1
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_feedback_loop_persists_state(self) -> None:
        """Verify state persists across loop instances."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            loop1 = CorrectionFeedbackLoop(state_file=state_file)
            loop1.record_correction("rate_limit", "Implement backoff")
            del loop1

            # New instance should load previous state
            loop2 = CorrectionFeedbackLoop(state_file=state_file)
            corrections = loop2.all_corrections()
            assert len(corrections) == 1
            assert corrections[0]["error_type"] == "rate_limit"
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_feedback_loop_records_effectiveness(self) -> None:
        """Verify effectiveness of corrections can be recorded."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            loop = CorrectionFeedbackLoop(state_file=state_file)
            suggestion_id = loop.record_correction("network_error", "Check connectivity")

            # Record outcomes
            loop.record_outcome(suggestion_id, success=True)
            loop.record_outcome(suggestion_id, success=True)
            loop.record_outcome(suggestion_id, success=False)

            effectiveness = loop.get_effectiveness(suggestion_id)
            assert effectiveness is not None
            assert effectiveness == 2 / 3  # 2 successes out of 3
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_feedback_loop_sorts_by_effectiveness(self) -> None:
        """Verify suggestions are sorted by effectiveness."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            loop = CorrectionFeedbackLoop(state_file=state_file)
            id1 = loop.record_correction("api_error", "Suggestion A - low effectiveness")
            id2 = loop.record_correction("api_error", "Suggestion B - high effectiveness")

            # id1 has low effectiveness (0.0), id2 has default (0.5)
            loop.record_outcome(id1, success=False)

            suggestions = loop.get_applicable_suggestions("api_error")
            assert suggestions[0]["suggestion_id"] == id2
            assert suggestions[1]["suggestion_id"] == id1
        finally:
            Path(state_file).unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# StateSnapshot Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestStateSnapshot:
    """Test suite for StateSnapshot."""

    def test_state_snapshot_captures_pre_and_post(self) -> None:
        """Verify pre and post states are captured correctly."""
        snap = StateSnapshot()

        pre = snap.capture_pre("gcloud compute instances list")
        assert pre is not None
        assert pre.timestamp is not None
        assert pre.command_hash is not None
        assert pre.working_dir == os.getcwd()
        assert pre.user is not None

        post = snap.capture_post("gcloud compute instances list")
        assert post is not None
        assert post.timestamp >= pre.timestamp
        assert post.command_hash == pre.command_hash

    def test_state_snapshot_compare_detects_git_changes(self) -> None:
        """Verify compare detects changes in git state."""
        snap = StateSnapshot()
        snap.capture_pre("git status")

        # Simulate a post state with different git status
        snap._post_state = StateSnapshotData(
            timestamp=datetime.now().isoformat(),
            command_hash="abc123",
            working_dir=os.getcwd(),
            user="testuser",
            git={
                "branch": "feature-branch",
                "has_uncommitted_changes": True,
                "uncommitted_files": ["modified_file.txt"],
                "stash_count": 0,
            },
            env={},
            gcloud={},
        )

        diff = snap.compare()
        assert diff["has_changes"] is True
        assert len(diff["differences"]) > 0

    def test_state_snapshot_compare_no_changes(self) -> None:
        """Verify compare returns no changes when states are identical."""
        snap = StateSnapshot()

        pre_state = StateSnapshotData(
            timestamp=datetime.now().isoformat(),
            command_hash="abc123",
            working_dir="/tmp",
            user="testuser",
            git={"branch": "main", "has_uncommitted_changes": False, "uncommitted_files": [], "stash_count": 0},
            env={},
            gcloud={},
        )
        snap._pre_state = pre_state
        snap._post_state = StateSnapshotData(
            timestamp=datetime.now().isoformat(),
            command_hash="abc123",
            working_dir="/tmp",
            user="testuser",
            git={"branch": "main", "has_uncommitted_changes": False, "uncommitted_files": [], "stash_count": 0},
            env={},
            gcloud={},
        )

        diff = snap.compare()
        assert diff["has_changes"] is False
        assert len(diff["differences"]) == 0

    def test_state_snapshot_compare_raises_without_pre(self) -> None:
        """Verify compare raises error if pre-state not captured."""
        snap = StateSnapshot()
        snap._post_state = StateSnapshotData(
            timestamp=datetime.now().isoformat(),
            command_hash="abc123",
            working_dir="/tmp",
            user="testuser",
            git={},
            env={},
            gcloud={},
        )

        with pytest.raises(RuntimeError, match="Pre-execution state not captured"):
            snap.compare()

    def test_state_snapshot_compare_raises_without_post(self) -> None:
        """Verify compare raises error if post-state not captured."""
        snap = StateSnapshot()
        snap._pre_state = StateSnapshotData(
            timestamp=datetime.now().isoformat(),
            command_hash="abc123",
            working_dir="/tmp",
            user="testuser",
            git={},
            env={},
            gcloud={},
        )

        with pytest.raises(RuntimeError, match="Post-execution state not captured"):
            snap.compare()


# ─────────────────────────────────────────────────────────────────────────────
# DegradationDetector Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDegradationDetector:
    """Test suite for DegradationDetector."""

    def test_degradation_detector_triggers_after_3_failures(self) -> None:
        """Verify degradation triggers after 3 consecutive failures of same type."""
        detector = DegradationDetector(threshold=3)

        # Record 2 failures - should not trigger
        detector.record_failure("timeout")
        assert detector.is_degraded() is False
        assert detector.get_consecutive_count("timeout") == 1

        detector.record_failure("timeout")
        assert detector.is_degraded() is False
        assert detector.get_consecutive_count("timeout") == 2

        # Third failure - should trigger
        detector.record_failure("timeout")
        assert detector.is_degraded() is True
        assert detector.get_consecutive_count("timeout") == 3

    def test_degradation_detector_resets_on_different_pattern(self) -> None:
        """Verify consecutive count resets when failure pattern changes."""
        detector = DegradationDetector(threshold=3)

        detector.record_failure("timeout")
        detector.record_failure("timeout")
        assert detector.get_consecutive_count("timeout") == 2

        # Different pattern resets timeout count
        detector.record_failure("auth_error")
        assert detector.get_consecutive_count("timeout") == 0
        assert detector.get_consecutive_count("auth_error") == 1

    def test_degradation_detector_generates_report(self) -> None:
        """Verify degradation report is generated correctly."""
        detector = DegradationDetector(threshold=3)

        detector.record_failure("rate_limit")
        detector.record_failure("rate_limit")
        detector.record_failure("rate_limit")

        assert detector.is_degraded() is True

        report = detector.generate_report()
        assert isinstance(report, DegradationReport)
        assert report.failure_pattern == "rate_limit"
        assert report.consecutive_failures == 3
        assert report.threshold == 3
        assert report.requires_human_review is True

    def test_degradation_detector_report_raises_when_not_degraded(self) -> None:
        """Verify generate_report raises when not degraded."""
        detector = DegradationDetector(threshold=3)
        detector.record_failure("timeout")

        with pytest.raises(RuntimeError, match="not in degraded state"):
            detector.generate_report()

    def test_degradation_detector_reset(self) -> None:
        """Verify reset clears all tracking state."""
        detector = DegradationDetector(threshold=2)
        detector.record_failure("timeout")
        detector.record_failure("timeout")

        assert detector.is_degraded() is True

        detector.reset()

        assert detector.is_degraded() is False
        assert detector.get_consecutive_count("timeout") == 0
        assert len(detector.get_failure_history()) == 0

    def test_degradation_detector_default_threshold(self) -> None:
        """Verify default threshold is 3."""
        detector = DegradationDetector()
        assert detector.get_threshold() == 3

    def test_degradation_detector_custom_threshold(self) -> None:
        """Verify custom threshold can be set."""
        detector = DegradationDetector(threshold=5)
        assert detector.get_threshold() == 5

    def test_degradation_detector_multiple_patterns(self) -> None:
        """Verify tracking of multiple failure patterns."""
        detector = DegradationDetector(threshold=2)

        detector.record_failure("timeout")
        detector.record_failure("auth_error")
        detector.record_failure("timeout")
        detector.record_failure("auth_error")

        # Neither reached threshold of 2 consecutively
        assert detector.is_degraded() is False

        # Another auth_error should trigger degradation
        detector.record_failure("auth_error")
        assert detector.is_degraded() is True
        assert detector.get_failure_pattern() == "auth_error"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSelfCorrectionMechanismIntegration:
    """Integration tests for the complete self-correction mechanism."""

    def test_full_correction_loop(self) -> None:
        """Verify complete loop: detect failure -> record correction -> apply -> record outcome."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        try:
            # Setup
            detector = DegradationDetector(threshold=2)
            loop = CorrectionFeedbackLoop(state_file=state_file)

            # Simulate failures and degradation
            detector.record_failure("timeout")
            detector.record_failure("timeout")

            assert detector.is_degraded() is True

            # Generate and record correction using analyze_and_suggest
            analysis = analyze_and_suggest({
                "error": {"code": -1, "status": "TIMEOUT", "message": "Connection timed out"},
                "operation": "gcloud compute instances list",
            })

            suggestion_id = loop.record_correction(
                error_type=analysis["error_type"],
                suggestion_text=analysis["suggestion"],
            )

            # Apply correction
            loop.mark_applied(suggestion_id)
            loop.record_outcome(suggestion_id, success=True)

            # Verify effectiveness recorded
            effectiveness = loop.get_effectiveness(suggestion_id)
            assert effectiveness == 1.0
        finally:
            Path(state_file).unlink(missing_ok=True)

    def test_state_snapshot_with_correction_feedback(self) -> None:
        """Verify state snapshot can be used alongside correction feedback."""
        snap = StateSnapshot()
        loop = CorrectionFeedbackLoop()

        # Capture pre-state
        pre = snap.capture_pre("gcloud compute instances list --limit=10")

        # Simulate execution with error
        error_type = "timeout"
        result = analyze_and_suggest({
            "error": {"code": -1, "status": "TIMEOUT", "message": "Connection timed out"},
            "operation": "gcloud compute instances list",
        })
        loop.record_correction(error_type, result["suggestion"])

        # Capture post-state
        post = snap.capture_post("gcloud compute instances list --limit=10")

        # Verify both states captured
        assert pre is not None
        assert post is not None
        assert pre.command_hash == post.command_hash

        # Verify correction recorded
        corrections = loop.all_corrections()
        assert len(corrections) == 1
        assert corrections[0]["error_type"] == "timeout"
