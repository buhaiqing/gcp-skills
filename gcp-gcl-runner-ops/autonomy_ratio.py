"""
Autonomy Ratio Calculation Module for GCL Runner.

This module provides autonomy ratio calculation, tracking, and alerting:
- AutonomyRatioCalculator: real-time calculation of autonomy ratio
- AutonomyRatioTracker: persistence with rolling window average
- AutonomyRatioAlert: threshold-based alerting for high autonomy ratios

Formula: (total_ops - degraded - safety_fails) / total_ops

Version: 1.0.0
Updated: 2026-07-19
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class AutonomyRatioCalculator:
    """Calculates autonomy ratio for a session.

    Formula: (total_ops - degraded - safety_fails) / total_ops
    """

    total_ops: int = 0
    degraded: int = 0
    safety_fails: int = 0

    def record_op(self, degraded: bool, safety_failed: bool) -> None:
        """Record a single operation outcome."""
        self.total_ops += 1
        if degraded:
            self.degraded += 1
        if safety_failed:
            self.safety_fails += 1

    @property
    def autonomy_ratio(self) -> float:
        """Calculate autonomy ratio.

        Returns 1.0 when no operations have been recorded.
        Clamps to 0.0 minimum when failures exceed operations.
        """
        if self.total_ops == 0:
            return 1.0
        ratio = (self.total_ops - self.degraded - self.safety_fails) / self.total_ops
        return max(0.0, ratio)

    def reset(self) -> None:
        """Reset all counters."""
        self.total_ops = 0
        self.degraded = 0
        self.safety_fails = 0

    def snapshot(self) -> dict[str, Any]:
        """Return current state as dictionary."""
        return {
            "total_ops": self.total_ops,
            "degraded": self.degraded,
            "safety_fails": self.safety_fails,
            "autonomy_ratio": self.autonomy_ratio,
        }


@dataclass
class AutonomyRatioTracker:
    """Persists autonomy ratio history with rolling window support.

    Tracks execution history to file and provides rolling window average.
    """

    history_file: str
    window_size: int = 100

    def __post_init__(self) -> None:
        """Initialize history list from file if exists."""
        self._ensure_history_file()
        self._history: list[dict[str, Any]] = self._load_history()

    def _ensure_history_file(self) -> None:
        """Create history file if it doesn't exist."""
        path = Path(self.history_file)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[]", encoding="utf-8")

    def _load_history(self) -> list[dict[str, Any]]:
        """Load history from file."""
        try:
            path = Path(self.history_file)
            if path.stat().st_size == 0:
                return []
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history(self) -> None:
        """Save history to file."""
        path = Path(self.history_file)
        path.write_text(json.dumps(self._history, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_execution(
        self,
        total_ops: int,
        degraded: int,
        safety_fails: int,
        timestamp: str | None = None,
    ) -> float:
        """Record an execution and update history.

        Args:
            total_ops: Total number of operations
            degraded: Number of degraded operations
            safety_fails: Number of safety failures
            timestamp: Optional ISO timestamp, defaults to current time

        Returns:
            The autonomy ratio for this execution
        """
        if timestamp is None:
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        if total_ops == 0:
            ratio = 1.0
        else:
            ratio = (total_ops - degraded - safety_fails) / total_ops

        record = {
            "timestamp": timestamp,
            "total_ops": total_ops,
            "degraded": degraded,
            "safety_fails": safety_fails,
            "autonomy_ratio": ratio,
        }

        self._history.append(record)

        # Trim to window size (keep most recent)
        if len(self._history) > self.window_size:
            self._history = self._history[-self.window_size :]

        self._save_history()
        return ratio

    def get_rolling_average(self) -> float:
        """Calculate rolling window average of autonomy ratio.

        Returns:
            Average autonomy ratio over the window, or 1.0 if no history.
        """
        if not self._history:
            return 1.0
        total = sum(r["autonomy_ratio"] for r in self._history)
        return total / len(self._history)

    def get_history(self) -> list[dict[str, Any]]:
        """Return full history."""
        return self._history.copy()

    def query_history(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query history with optional filters.

        Args:
            start_time: Filter records after this ISO timestamp
            end_time: Filter records before this ISO timestamp
            limit: Maximum number of records to return

        Returns:
            Filtered list of history records
        """
        results = self._history.copy()

        if start_time:
            results = [r for r in results if r["timestamp"] >= start_time]
        if end_time:
            results = [r for r in results if r["timestamp"] <= end_time]

        # Most recent first
        results = list(reversed(results))

        if limit is not None:
            results = results[:limit]

        return results


@dataclass
class AutonomyRatioAlert:
    """Alert when autonomy ratio exceeds threshold (requires human review).

    A high autonomy ratio (> threshold) indicates the agent is operating
    with minimal degradation/safety failures, which should trigger review.
    """

    threshold: float = 0.9
    pending_alerts: list[dict[str, Any]] = field(default_factory=list)

    def check_ratio(
        self,
        autonomy_ratio: float,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Check if ratio exceeds threshold and create alert if needed.

        Args:
            autonomy_ratio: The autonomy ratio to check
            execution_id: Unique identifier for this execution

        Returns:
            Alert dict if ratio > threshold, None otherwise
        """
        if autonomy_ratio > self.threshold:
            alert = {
                "execution_id": execution_id,
                "autonomy_ratio": autonomy_ratio,
                "threshold": self.threshold,
                "requires_review": True,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            self.pending_alerts.append(alert)
            return alert
        return None

    def acknowledge(self, execution_id: str) -> bool:
        """Acknowledge and remove a specific alert.

        Args:
            execution_id: The execution ID to acknowledge

        Returns:
            True if found and removed, False if not found
        """
        for i, alert in enumerate(self.pending_alerts):
            if alert["execution_id"] == execution_id:
                self.pending_alerts.pop(i)
                return True
        return False

    def clear_alerts(self) -> None:
        """Clear all pending alerts."""
        self.pending_alerts.clear()

    def get_pending_count(self) -> int:
        """Return number of pending alerts."""
        return len(self.pending_alerts)
