"""
Tests for Autonomy Ratio calculation module.

Tests cover:
- test_autonomy_ratio_calculation: basic formula validation
- test_autonomy_ratio_tracker_persistence: file persistence + rolling window
- test_autonomy_ratio_alert_threshold: alert triggering at threshold
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from autonomy_ratio import (
    AutonomyRatioAlert,
    AutonomyRatioCalculator,
    AutonomyRatioTracker,
)


class TestAutonomyRatioCalculator:
    """Tests for AutonomyRatioCalculator."""

    def test_autonomy_ratio_calculation(self) -> None:
        """Test basic autonomy ratio formula: (total_ops - degraded - safety_fails) / total_ops."""
        calc = AutonomyRatioCalculator()

        # Case 1: Perfect ratio (all operations successful)
        calc.record_op(degraded=False, safety_failed=False)
        calc.record_op(degraded=False, safety_failed=False)
        calc.record_op(degraded=False, safety_failed=False)
        assert calc.total_ops == 3
        assert calc.autonomy_ratio == 1.0

        # Case 2: Some degraded operations
        calc2 = AutonomyRatioCalculator()
        calc2.record_op(degraded=True, safety_failed=False)  # 1 degraded
        calc2.record_op(degraded=False, safety_failed=False)  # 1 normal
        calc2.record_op(degraded=False, safety_failed=False)  # 1 normal
        assert calc2.total_ops == 3
        assert calc2.autonomy_ratio == pytest.approx(2 / 3)

        # Case 3: Safety failures
        calc3 = AutonomyRatioCalculator()
        calc3.record_op(degraded=False, safety_failed=True)  # 1 safety fail
        calc3.record_op(degraded=False, safety_failed=False)  # 1 normal
        calc3.record_op(degraded=False, safety_failed=False)  # 1 normal
        assert calc3.total_ops == 3
        assert calc3.autonomy_ratio == pytest.approx(2 / 3)

        # Case 4: Both degraded and safety failures
        calc4 = AutonomyRatioCalculator()
        calc4.record_op(degraded=True, safety_failed=False)  # 1 degraded
        calc4.record_op(degraded=False, safety_failed=True)  # 1 safety fail
        calc4.record_op(degraded=False, safety_failed=False)  # 1 normal
        assert calc4.total_ops == 3
        assert calc4.autonomy_ratio == pytest.approx(1 / 3)

        # Case 5: Zero operations should return 1.0 (no failures)
        calc5 = AutonomyRatioCalculator()
        assert calc5.autonomy_ratio == 1.0

        # Case 6: All operations failed
        calc6 = AutonomyRatioCalculator()
        calc6.record_op(degraded=True, safety_failed=False)
        calc6.record_op(degraded=False, safety_failed=True)
        calc6.record_op(degraded=True, safety_failed=True)
        assert calc6.total_ops == 3
        assert calc6.autonomy_ratio == 0.0

    def test_calculator_resets_counters(self) -> None:
        """Test that reset clears all counters."""
        calc = AutonomyRatioCalculator()
        calc.record_op(degraded=True, safety_failed=False)
        calc.record_op(degraded=False, safety_failed=False)
        assert calc.total_ops == 2
        calc.reset()
        assert calc.total_ops == 0
        assert calc.autonomy_ratio == 1.0

    def test_calculator_snapshot(self) -> None:
        """Test snapshot returns current state dict."""
        calc = AutonomyRatioCalculator()
        calc.record_op(degraded=True, safety_failed=False)
        calc.record_op(degraded=False, safety_failed=False)
        snapshot = calc.snapshot()
        assert snapshot["total_ops"] == 2
        assert snapshot["degraded"] == 1
        assert snapshot["safety_fails"] == 0
        assert snapshot["autonomy_ratio"] == pytest.approx(0.5)


class TestAutonomyRatioTrackerPersistence:
    """Tests for AutonomyRatioTracker persistence and rolling window."""

    def test_autonomy_ratio_tracker_persistence(self) -> None:
        """Test persistence to file and rolling window average."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_file = Path(tmpdir) / "autonomy_history.json"

            # Create tracker with rolling window of 5
            tracker = AutonomyRatioTracker(
                history_file=str(tracker_file),
                window_size=5,
            )

            # Record several executions
            tracker.record_execution(
                total_ops=10, degraded=1, safety_fails=0
            )  # ratio = 0.9
            tracker.record_execution(
                total_ops=10, degraded=0, safety_fails=0
            )  # ratio = 1.0
            tracker.record_execution(
                total_ops=10, degraded=2, safety_fails=0
            )  # ratio = 0.8
            tracker.record_execution(
                total_ops=10, degraded=0, safety_fails=0
            )  # ratio = 1.0
            tracker.record_execution(
                total_ops=10, degraded=1, safety_fails=0
            )  # ratio = 0.9

            # Check rolling average (last 5)
            avg = tracker.get_rolling_average()
            expected_avg = (0.9 + 1.0 + 0.8 + 1.0 + 0.9) / 5
            assert avg == pytest.approx(expected_avg)

            # Check history count
            history = tracker.get_history()
            assert len(history) == 5

            # Create new tracker instance to verify persistence
            tracker2 = AutonomyRatioTracker(
                history_file=str(tracker_file),
                window_size=5,
            )
            history2 = tracker2.get_history()
            assert len(history2) == 5

            # Rolling average should still work
            avg2 = tracker2.get_rolling_average()
            assert avg2 == pytest.approx(expected_avg)

    def test_rolling_window_respects_limit(self) -> None:
        """Test that rolling window respects the size limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_file = Path(tmpdir) / "autonomy_history.json"

            # Window size of 3
            tracker = AutonomyRatioTracker(
                history_file=str(tracker_file),
                window_size=3,
            )

            # Record 5 executions
            for i in range(5):
                degraded = 1 if i % 2 == 0 else 0
                tracker.record_execution(
                    total_ops=10, degraded=degraded, safety_fails=0
                )

            # Should only keep last 3
            history = tracker.get_history()
            assert len(history) == 3

            # Rolling average of last 3
            avg = tracker.get_rolling_average()
            # Last 3: ratios are 0.9, 1.0, 0.9
            expected_avg = (0.9 + 1.0 + 0.9) / 3
            assert avg == pytest.approx(expected_avg)

    def test_history_query_by_date_range(self) -> None:
        """Test querying history within date range."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_file = Path(tmpdir) / "autonomy_history.json"

            tracker = AutonomyRatioTracker(
                history_file=str(tracker_file),
                window_size=10,
            )

            # Record some executions (timestamps are auto-generated)
            tracker.record_execution(total_ops=10, degraded=1, safety_fails=0)
            tracker.record_execution(total_ops=10, degraded=0, safety_fails=0)
            tracker.record_execution(total_ops=10, degraded=2, safety_fails=0)

            # Query all
            all_records = tracker.query_history()
            assert len(all_records) == 3

            # Query with limit
            limited = tracker.query_history(limit=2)
            assert len(limited) == 2


class TestAutonomyRatioAlert:
    """Tests for AutonomyRatioAlert threshold alerting."""

    def test_autonomy_ratio_alert_threshold(self) -> None:
        """Test alert triggering when ratio exceeds threshold (high autonomy = needs review)."""
        alert = AutonomyRatioAlert(threshold=0.9)

        # Case 1: Ratio below threshold (no alert needed)
        alert.check_ratio(autonomy_ratio=0.85, execution_id="exec-1")
        assert len(alert.pending_alerts) == 0

        # Case 2: Ratio above threshold (needs alert - ratio > threshold triggers)
        alert2 = AutonomyRatioAlert(threshold=0.9)
        alert2.check_ratio(autonomy_ratio=0.91, execution_id="exec-2")
        assert len(alert2.pending_alerts) == 1
        assert alert2.pending_alerts[0]["execution_id"] == "exec-2"
        assert alert2.pending_alerts[0]["autonomy_ratio"] == 0.91
        assert alert2.pending_alerts[0]["threshold"] == 0.9

        # Case 3: Ratio above threshold (alert triggered)
        alert3 = AutonomyRatioAlert(threshold=0.9)
        alert3.check_ratio(autonomy_ratio=0.95, execution_id="exec-3")
        assert len(alert3.pending_alerts) == 1

    def test_custom_threshold(self) -> None:
        """Test custom threshold configuration."""
        # High threshold (99%) - 0.98 does not exceed 0.99
        alert_high = AutonomyRatioAlert(threshold=0.99)
        alert_high.check_ratio(autonomy_ratio=0.98, execution_id="exec-high")
        assert len(alert_high.pending_alerts) == 0

        # Low threshold (50%) - 0.98 exceeds 0.5
        alert_low = AutonomyRatioAlert(threshold=0.5)
        alert_low.check_ratio(autonomy_ratio=0.98, execution_id="exec-low")
        assert len(alert_low.pending_alerts) == 1

        # Ratio exactly at threshold (0.5) should not trigger (0.5 > 0.5 is false)
        alert_low.check_ratio(autonomy_ratio=0.5, execution_id="exec-exact")
        assert len(alert_low.pending_alerts) == 1  # Still 1, no new alert added

    def test_alert_clear(self) -> None:
        """Test clearing pending alerts."""
        alert = AutonomyRatioAlert(threshold=0.9)
        alert.check_ratio(autonomy_ratio=0.95, execution_id="exec-1")
        alert.check_ratio(autonomy_ratio=0.92, execution_id="exec-2")
        assert len(alert.pending_alerts) == 2

        # Clear alerts
        alert.clear_alerts()
        assert len(alert.pending_alerts) == 0

    def test_alert_acknowledgment(self) -> None:
        """Test acknowledging specific alerts."""
        alert = AutonomyRatioAlert(threshold=0.9)
        alert.check_ratio(autonomy_ratio=0.95, execution_id="exec-1")
        alert.check_ratio(autonomy_ratio=0.92, execution_id="exec-2")

        # Acknowledge one
        alert.acknowledge(execution_id="exec-1")
        assert len(alert.pending_alerts) == 1
        assert alert.pending_alerts[0]["execution_id"] == "exec-2"

    def test_alert_requires_review_flag(self) -> None:
        """Test that high autonomy ratio (> threshold) triggers requires_review flag."""
        alert = AutonomyRatioAlert(threshold=0.9)

        # Ratio above threshold should trigger requires_review
        result = alert.check_ratio(autonomy_ratio=0.95, execution_id="exec-1")
        assert result is not None
        assert result["requires_review"] is True

        # Ratio below threshold should not trigger
        alert2 = AutonomyRatioAlert(threshold=0.9)
        result2 = alert2.check_ratio(autonomy_ratio=0.85, execution_id="exec-2")
        assert result2 is None
