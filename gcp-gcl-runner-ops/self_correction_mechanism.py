"""
Self-correction mechanism for GCL Runner.

This module implements the self-correction mechanism with three main components:
1. CorrectionFeedbackLoop - records and applies correction suggestions
2. StateSnapshot - captures pre/post execution state and compares differences
3. DegradationDetector - tracks failure patterns and triggers degradation alerts

Dependencies:
- self_correction.py (P1-1.4): Provides correction suggestion generation via
  CorrectionSuggestionGenerator and analyze_and_suggest
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from self_correction import (
    CorrectionSuggestionGenerator,
    SuggestionOutput,
)

# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class StateSnapshotData:
    """Represents a state snapshot with pre/post execution data."""

    timestamp: str
    command_hash: str
    working_dir: str
    user: str
    git: dict[str, Any]
    env: dict[str, Any]
    gcloud: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "command_hash": self.command_hash,
            "working_dir": self.working_dir,
            "user": self.user,
            "git": self.git,
            "env": self.env,
            "gcloud": self.gcloud,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateSnapshotData:
        return cls(
            timestamp=data["timestamp"],
            command_hash=data["command_hash"],
            working_dir=data["working_dir"],
            user=data["user"],
            git=data["git"],
            env=data["env"],
            gcloud=data["gcloud"],
            extra=data.get("extra", {}),
        )


@dataclass
class DegradationReport:
    """Report generated when degradation is detected."""

    failure_pattern: str
    consecutive_failures: int
    threshold: int
    requires_human_review: bool
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    details: dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# CorrectionFeedbackLoop
# ─────────────────────────────────────────────────────────────────────────────


class CorrectionFeedbackLoop:
    """
    Records correction suggestions from execution feedback and applies them
    on subsequent executions.

    Usage:
        loop = CorrectionFeedbackLoop(state_file="correction_state.json")
        loop.record_correction("timeout", "Increase timeout value")
        suggestions = loop.get_applicable_suggestions("timeout")
    """

    def __init__(self, state_file: str | Path | None = None) -> None:
        """
        Initialize the correction feedback loop.

        Args:
            state_file: Optional path to persist correction state across sessions.
        """
        self.state_file = Path(state_file) if state_file else None
        self._corrections: list[dict[str, Any]] = []
        self._correction_effectiveness: dict[str, list[bool]] = {}
        self._suggestion_generator = CorrectionSuggestionGenerator()
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted correction state from file."""
        if self.state_file and self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._corrections = data.get("corrections", [])
                self._correction_effectiveness = data.get("effectiveness", {})
            except (json.JSONDecodeError, OSError):
                self._corrections = []
                self._correction_effectiveness = {}

    def _save_state(self) -> None:
        """Persist correction state to file."""
        if self.state_file:
            data = {
                "corrections": self._corrections,
                "effectiveness": self._correction_effectiveness,
            }
            self.state_file.write_text(json.dumps(data, indent=2))

    def record_correction(
        self, error_type: str, suggestion_text: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Record a correction suggestion.

        Args:
            error_type: The type of error this correction addresses
            suggestion_text: The correction suggestion text
            context: Optional context about the execution

        Returns:
            The suggestion_id of the recorded correction
        """
        suggestion_id = f"suggestion_{int(datetime.now().timestamp() * 1000)}"
        record = {
            "suggestion_id": suggestion_id,
            "error_type": error_type,
            "suggestion_text": suggestion_text,
            "context": context or {},
            "recorded_at": datetime.now().isoformat(),
            "applied": False,
            "applied_count": 0,
        }
        self._corrections.append(record)
        self._save_state()
        return suggestion_id

    def get_applicable_suggestions(self, error_type: str) -> list[dict[str, Any]]:
        """
        Get correction suggestions applicable for an error type.

        Args:
            error_type: The error type to get suggestions for

        Returns:
            List of correction records ordered by effectiveness (most effective first)
        """
        applicable = [c for c in self._corrections if c["error_type"] == error_type]

        def effectiveness_score(c: dict[str, Any]) -> float:
            scores = self._correction_effectiveness.get(c["suggestion_id"], [])
            if not scores:
                return 0.5  # Default score for untested corrections
            return sum(scores) / len(scores)

        applicable.sort(key=effectiveness_score, reverse=True)
        return applicable

    def mark_applied(self, suggestion_id: str) -> bool:
        """
        Mark a correction as applied.

        Args:
            suggestion_id: The suggestion to mark as applied

        Returns:
            True if found and marked, False otherwise
        """
        for correction in self._corrections:
            if correction["suggestion_id"] == suggestion_id:
                correction["applied"] = True
                correction["applied_count"] = correction.get("applied_count", 0) + 1
                self._save_state()
                return True
        return False

    def record_outcome(self, suggestion_id: str, success: bool) -> None:
        """
        Record whether a correction was effective.

        Args:
            suggestion_id: The suggestion that was applied
            success: Whether the correction resolved the issue
        """
        if suggestion_id not in self._correction_effectiveness:
            self._correction_effectiveness[suggestion_id] = []
        self._correction_effectiveness[suggestion_id].append(success)
        self._save_state()

    def get_effectiveness(self, suggestion_id: str) -> float | None:
        """
        Get the effectiveness score for a suggestion.

        Args:
            suggestion_id: The suggestion to evaluate

        Returns:
            Effectiveness score 0.0-1.0, or None if no data
        """
        scores = self._correction_effectiveness.get(suggestion_id, [])
        if not scores:
            return None
        return sum(scores) / len(scores)

    def all_corrections(self) -> list[dict[str, Any]]:
        """Return all recorded corrections."""
        return list(self._corrections)

    def generate_suggestion(self, error_context: dict[str, Any]) -> SuggestionOutput:
        """
        Generate a correction suggestion for an error context.

        Args:
            error_context: Dict containing 'error' and 'operation' keys.

        Returns:
            SuggestionOutput with structured suggestion, confidence, and references.
        """
        return self._suggestion_generator.generate(error_context)


# ─────────────────────────────────────────────────────────────────────────────
# StateSnapshot
# ─────────────────────────────────────────────────────────────────────────────


class StateSnapshot:
    """
    Captures system state before and after execution and compares differences.

    Usage:
        snap = StateSnapshot()
        snap.capture_pre("gcloud compute instances list")
        # ... execute command ...
        snap.capture_post("gcloud compute instances list")
        diff = snap.compare()
    """

    def __init__(self) -> None:
        self._pre_state: StateSnapshotData | None = None
        self._post_state: StateSnapshotData | None = None
        self._last_command: str | None = None

    def capture_pre(self, command: str, extra: dict[str, Any] | None = None) -> StateSnapshotData:
        """
        Capture pre-execution state.

        Args:
            command: The command to be executed
            extra: Optional additional state data

        Returns:
            The captured pre-state snapshot
        """
        import getpass
        import os

        self._last_command = command
        timestamp = datetime.now().isoformat()
        command_hash = hashlib.sha256(command.encode()).hexdigest()[:12]

        git_status = self._capture_git_status()
        env_vars = self._capture_gcp_env_vars()
        gcloud_config = self._capture_gcloud_config()

        self._pre_state = StateSnapshotData(
            timestamp=timestamp,
            command_hash=command_hash,
            working_dir=os.getcwd(),
            user=getpass.getuser(),
            git=git_status,
            env=env_vars,
            gcloud=gcloud_config,
            extra=extra or {},
        )
        return self._pre_state

    def capture_post(self, command: str, extra: dict[str, Any] | None = None) -> StateSnapshotData:
        """
        Capture post-execution state.

        Args:
            command: The command that was executed
            extra: Optional additional state data

        Returns:
            The captured post-state snapshot
        """
        import getpass
        import os

        timestamp = datetime.now().isoformat()
        command_hash = hashlib.sha256(command.encode()).hexdigest()[:12]

        git_status = self._capture_git_status()
        env_vars = self._capture_gcp_env_vars()
        gcloud_config = self._capture_gcloud_config()

        self._post_state = StateSnapshotData(
            timestamp=timestamp,
            command_hash=command_hash,
            working_dir=os.getcwd(),
            user=getpass.getuser(),
            git=git_status,
            env=env_vars,
            gcloud=gcloud_config,
            extra=extra or {},
        )
        return self._post_state

    def _capture_git_status(self) -> dict[str, Any]:
        """Capture current git status."""
        import subprocess

        git_status: dict[str, Any] = {
            "branch": "unknown",
            "has_uncommitted_changes": False,
            "uncommitted_files": [],
            "stash_count": 0,
        }
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            git_status["has_uncommitted_changes"] = bool(result.stdout.strip())
            git_status["uncommitted_files"] = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            git_status["branch"] = branch_result.stdout.strip() or "unknown"
            stash_result = subprocess.run(
                ["git", "stash", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            git_status["stash_count"] = (
                len(stash_result.stdout.strip().split("\n")) if stash_result.stdout.strip() else 0
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        return git_status

    def _capture_gcp_env_vars(self) -> dict[str, str]:
        """Capture GCP-related environment variables."""
        import os

        env_vars: dict[str, str] = {}
        gcp_prefixes = ["CLOUDSDK_", "GCP_", "GOOGLE_", "GCLOUD_"]
        sensitive_keys = {
            "GOOGLE_APPLICATION_CREDENTIALS",
            "CLOUDSDK_API_KEY",
            "GOOGLE_TOKEN",
            "GOOGLE_API_KEY",
        }
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in gcp_prefixes):
                env_vars[key] = "<masked>" if key in sensitive_keys else value
        return env_vars

    def _capture_gcloud_config(self) -> dict[str, Any]:
        """Capture gcloud configuration."""
        import json
        import subprocess

        gcloud_config: dict[str, Any] = {
            "active_configuration": "unknown",
            "project": None,
            "region": None,
            "zone": None,
            "account": None,
        }
        try:
            result = subprocess.run(
                ["gcloud", "config", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                config_data = json.loads(result.stdout)
                gcloud_config["active_configuration"] = (
                    config_data.get("core", {}).get("configuration", {}).get("name", "default")
                )
                gcloud_config["project"] = config_data.get("core", {}).get("project", None)
                gcloud_config["region"] = config_data.get("compute", {}).get("region", None)
                gcloud_config["zone"] = config_data.get("compute", {}).get("zone", None)
                gcloud_config["account"] = config_data.get("core", {}).get("account", None)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
            gcloud_config["error"] = "unavailable"
        return gcloud_config

    def compare(self) -> dict[str, Any]:
        """
        Compare pre and post execution states.

        Returns:
            Dict with 'has_changes', 'differences' list, and summary

        Raises:
            RuntimeError: If pre or post state not captured
        """
        if self._pre_state is None:
            raise RuntimeError("Pre-execution state not captured. Call capture_pre() first.")
        if self._post_state is None:
            raise RuntimeError("Post-execution state not captured. Call capture_post() first.")

        differences: list[dict[str, Any]] = []

        # Compare git branch
        if self._pre_state.git.get("branch") != self._post_state.git.get("branch"):
            differences.append({
                "field": "git.branch",
                "before": self._pre_state.git.get("branch"),
                "after": self._post_state.git.get("branch"),
            })

        # Compare uncommitted changes
        pre_uncommitted = self._pre_state.git.get("has_uncommitted_changes", False)
        post_uncommitted = self._post_state.git.get("has_uncommitted_changes", False)
        if pre_uncommitted != post_uncommitted:
            differences.append({
                "field": "git.has_uncommitted_changes",
                "before": pre_uncommitted,
                "after": post_uncommitted,
            })

        # Compare uncommitted files
        pre_files = set(self._pre_state.git.get("uncommitted_files", []))
        post_files = set(self._post_state.git.get("uncommitted_files", []))
        if pre_files != post_files:
            differences.append({
                "field": "git.uncommitted_files",
                "before": list(pre_files),
                "after": list(post_files),
                "added": list(post_files - pre_files),
                "removed": list(pre_files - post_files),
            })

        # Compare stash count
        pre_stash = self._pre_state.git.get("stash_count", 0)
        post_stash = self._post_state.git.get("stash_count", 0)
        if pre_stash != post_stash:
            differences.append({
                "field": "git.stash_count",
                "before": pre_stash,
                "after": post_stash,
            })

        # Compare working directory
        if self._pre_state.working_dir != self._post_state.working_dir:
            differences.append({
                "field": "working_dir",
                "before": self._pre_state.working_dir,
                "after": self._post_state.working_dir,
            })

        return {
            "has_changes": len(differences) > 0,
            "differences": differences,
            "summary": f"Found {len(differences)} difference(s)",
        }

    def get_pre_state(self) -> StateSnapshotData | None:
        """Get the captured pre-execution state."""
        return self._pre_state

    def get_post_state(self) -> StateSnapshotData | None:
        """Get the captured post-execution state."""
        return self._post_state


# ─────────────────────────────────────────────────────────────────────────────
# DegradationDetector
# ─────────────────────────────────────────────────────────────────────────────


class DegradationDetector:
    """
    Detects degradation patterns by tracking consecutive failures.

    Triggers human review when same failure pattern occurs 3+ times consecutively.

    Usage:
        detector = DegradationDetector()
        detector.record_failure("timeout", {"command": "gcloud compute instances list"})
        if detector.is_degraded():
            report = detector.generate_report()
    """

    DEFAULT_THRESHOLD = 3

    def __init__(self, threshold: int | None = None) -> None:
        """
        Initialize the degradation detector.

        Args:
            threshold: Number of consecutive failures before triggering degradation.
                      Defaults to 3.
        """
        self._threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD
        self._failure_history: list[dict[str, Any]] = []
        self._consecutive_failures: dict[str, int] = {}
        self._last_failure_pattern: str | None = None

    def record_failure(self, error_type: str, context: dict[str, Any] | None = None) -> None:
        """
        Record a failure occurrence.

        Args:
            error_type: The type/category of the failure
            context: Optional context about the failure
        """
        failure_record = {
            "error_type": error_type,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._failure_history.append(failure_record)

        # Update consecutive failure count
        if error_type == self._last_failure_pattern:
            self._consecutive_failures[error_type] = self._consecutive_failures.get(error_type, 0) + 1
        else:
            # Reset other patterns, start counting this one
            for pattern in self._consecutive_failures:
                if pattern != error_type:
                    self._consecutive_failures[pattern] = 0
            self._consecutive_failures[error_type] = 1

        self._last_failure_pattern = error_type

    def is_degraded(self) -> bool:
        """
        Check if degradation threshold has been reached.

        Returns:
            True if any failure pattern has reached the threshold
        """
        return any(count >= self._threshold for count in self._consecutive_failures.values())

    def get_consecutive_count(self, error_type: str) -> int:
        """
        Get the consecutive failure count for a specific error type.

        Args:
            error_type: The error type to check

        Returns:
            Number of consecutive failures of this type
        """
        return self._consecutive_failures.get(error_type, 0)

    def get_failure_pattern(self) -> str | None:
        """
        Get the current dominant failure pattern.

        Returns:
            The error type with highest consecutive count, or None
        """
        if not self._consecutive_failures:
            return None
        return max(self._consecutive_failures, key=self._consecutive_failures.get)

    def get_threshold(self) -> int:
        """Get the configured degradation threshold."""
        return self._threshold

    def generate_report(self) -> DegradationReport:
        """
        Generate a degradation report.

        Returns:
            DegradationReport with details of the degradation state

        Raises:
            RuntimeError: If not in degraded state
        """
        if not self.is_degraded():
            raise RuntimeError("System is not in degraded state")

        dominant_pattern = self.get_failure_pattern()
        if dominant_pattern is None:
            raise RuntimeError("No failure pattern found")

        consecutive = self._consecutive_failures[dominant_pattern]

        # Gather context of recent failures
        recent_failures = [
            f for f in self._failure_history if f["error_type"] == dominant_pattern
        ][-consecutive:]

        return DegradationReport(
            failure_pattern=dominant_pattern,
            consecutive_failures=consecutive,
            threshold=self._threshold,
            requires_human_review=True,
            details={
                "recent_failures": recent_failures,
                "total_failures": len(self._failure_history),
                "all_patterns": dict(self._consecutive_failures),
            },
        )

    def reset(self) -> None:
        """Reset all failure tracking state."""
        self._failure_history.clear()
        self._consecutive_failures.clear()
        self._last_failure_pattern = None

    def get_failure_history(self) -> list[dict[str, Any]]:
        """Get the complete failure history."""
        return list(self._failure_history)
