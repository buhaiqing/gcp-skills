#!/usr/bin/env python3
"""
Tests for state snapshot functionality in Enhanced GCL Runner.

These tests verify that the state snapshot captures required fields
and properly masks sensitive values.
Run with: python -m pytest tests/test_state_snapshot.py -v
"""

from __future__ import annotations

import os

# Import the module under test
import sys
from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from gcl_runner_enhanced import (
    _capture_gcloud_config,
    _capture_gcp_env_vars,
    _capture_git_status,
    generate_state_snapshot,
)


class TestGenerateStateSnapshot:
    """Test suite for generate_state_snapshot function."""

    def test_snapshot_contains_required_fields(self) -> None:
        """Verify snapshot captures all required fields."""
        snapshot = generate_state_snapshot("gcloud compute instances list")

        # Check top-level fields
        assert "timestamp" in snapshot, "Missing timestamp field"
        assert "command_hash" in snapshot, "Missing command_hash field"
        assert "working_dir" in snapshot, "Missing working_dir field"
        assert "user" in snapshot, "Missing user field"

        # Check nested structures
        assert "git" in snapshot, "Missing git field"
        assert "env" in snapshot, "Missing env field"
        assert "gcloud" in snapshot, "Missing gcloud field"

    def test_timestamp_is_iso8601(self) -> None:
        """Verify timestamp is valid ISO 8601 format."""
        snapshot = generate_state_snapshot("gcloud compute instances list")
        ts = snapshot["timestamp"]
        # Should not raise if valid
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_working_dir_is_string(self) -> None:
        """Verify working_dir is a valid string path."""
        snapshot = generate_state_snapshot("gcloud compute instances list")
        assert isinstance(snapshot["working_dir"], str)
        assert len(snapshot["working_dir"]) > 0

    def test_command_hash_is_deterministic(self) -> None:
        """Verify same command produces same hash."""
        cmd = "gcloud compute instances list"
        snapshot1 = generate_state_snapshot(cmd)
        snapshot2 = generate_state_snapshot(cmd)
        assert snapshot1["command_hash"] == snapshot2["command_hash"]

    def test_different_commands_different_hashes(self) -> None:
        """Verify different commands produce different hashes."""
        snapshot1 = generate_state_snapshot("gcloud compute instances list")
        snapshot2 = generate_state_snapshot("gcloud compute instances describe")
        assert snapshot1["command_hash"] != snapshot2["command_hash"]


class TestCaptureGitStatus:
    """Test suite for _capture_git_status function."""

    def test_git_status_contains_required_fields(self) -> None:
        """Verify git status captures required fields."""
        status = _capture_git_status()

        assert "branch" in status, "Missing branch field"
        assert "has_uncommitted_changes" in status, "Missing has_uncommitted_changes field"
        assert "uncommitted_files" in status, "Missing uncommitted_files field"
        assert "stash_count" in status, "Missing stash_count field"

    def test_git_status_types(self) -> None:
        """Verify git status field types."""
        status = _capture_git_status()

        assert isinstance(status["branch"], str), "branch should be string"
        assert isinstance(status["has_uncommitted_changes"], bool), "has_uncommitted_changes should be bool"
        assert isinstance(status["uncommitted_files"], list), "uncommitted_files should be list"
        assert isinstance(status["stash_count"], int), "stash_count should be int"


class TestCaptureGCPAEnvVars:
    """Test suite for _capture_gcp_env_vars function."""

    def test_filters_non_gcp_vars(self) -> None:
        """Verify only GCP-related vars are included."""
        env_vars = _capture_gcp_env_vars()

        gcp_prefixes = ["CLOUDSDK_", "GCP_", "GOOGLE_", "GCLOUD_"]
        for key in env_vars.keys():
            assert any(key.startswith(prefix) for prefix in gcp_prefixes), \
                f"Non-GCP variable found: {key}"

    def test_masks_sensitive_values(self) -> None:
        """Verify sensitive values are masked."""
        # Set a sensitive GCP env var
        with patch.dict(os.environ, {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json",
            "CLOUDSDK_API_KEY": "secret123",
            "GOOGLE_TOKEN": "ya29.secret",
            "CLOUDSDK_CORE_PROJECT": "my-project",
        }, clear=False):
            env_vars = _capture_gcp_env_vars()

        # Sensitive values should be masked
        assert env_vars.get("GOOGLE_APPLICATION_CREDENTIALS") == "<masked>"
        assert env_vars.get("CLOUDSDK_API_KEY") == "<masked>"
        assert env_vars.get("GOOGLE_TOKEN") == "<masked>"
        # Non-sensitive should not be masked
        assert env_vars.get("CLOUDSDK_CORE_PROJECT") == "my-project"

    def test_preserves_non_sensitive_gcp_vars(self) -> None:
        """Verify non-sensitive GCP vars are preserved."""
        with patch.dict(os.environ, {
            "CLOUDSDK_CORE_PROJECT": "my-project",
            "CLOUDSDK_COMPUTE_REGION": "us-central1",
            "GOOGLE_CLOUD_PROJECT": "another-project",
        }, clear=False):
            env_vars = _capture_gcp_env_vars()

        assert env_vars.get("CLOUDSDK_CORE_PROJECT") == "my-project"
        assert env_vars.get("CLOUDSDK_COMPUTE_REGION") == "us-central1"
        assert env_vars.get("GOOGLE_CLOUD_PROJECT") == "another-project"


class TestCaptureGcloudConfig:
    """Test suite for _capture_gcloud_config function."""

    def test_config_contains_required_fields(self) -> None:
        """Verify gcloud config captures required fields."""
        config = _capture_gcloud_config()

        assert "active_configuration" in config, "Missing active_configuration field"
        assert "project" in config, "Missing project field"
        assert "region" in config, "Missing region field"
        assert "zone" in config, "Missing zone field"
        assert "account" in config, "Missing account field"

    def test_config_handles_missing_gcloud(self) -> None:
        """Verify graceful handling when gcloud is unavailable."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gcloud not found")
            config = _capture_gcloud_config()

        assert "error" in config, "Should have error field when gcloud unavailable"
        assert config["active_configuration"] == "unknown"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_snapshot() -> dict[str, Any]:
    """Sample state snapshot for testing."""
    return {
        "timestamp": datetime.now().isoformat(),
        "command_hash": "1234567890",
        "working_dir": "/tmp",
        "user": "testuser",
        "git": {
            "branch": "main",
            "has_uncommitted_changes": False,
            "uncommitted_files": [],
            "stash_count": 0,
        },
        "env": {
            "CLOUDSDK_CORE_PROJECT": "test-project",
        },
        "gcloud": {
            "active_configuration": "default",
            "project": "test-project",
            "region": "us-central1",
            "zone": None,
            "account": "test@example.com",
        },
    }


class TestSnapshotIntegration:
    """Integration tests for snapshot with trace."""

    def test_snapshot_can_be_added_to_trace(self, sample_snapshot: dict[str, Any]) -> None:
        """Verify snapshot can be added to trace dict."""
        trace_dict: dict[str, Any] = {
            "trace_id": "test-trace",
            "timestamp": datetime.now().isoformat(),
            "iterations": [],
        }

        # Add pre/post state
        trace_dict["pre_state"] = sample_snapshot
        trace_dict["post_state"] = sample_snapshot

        assert "pre_state" in trace_dict
        assert "post_state" in trace_dict
        assert trace_dict["pre_state"]["git"]["branch"] == "main"
        assert trace_dict["post_state"]["git"]["branch"] == "main"
