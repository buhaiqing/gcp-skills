#!/usr/bin/env python3
"""
Tests for BigQuery trace upload functionality.

Run with: python -m pytest tests/test_bq_upload.py -v
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gcl_trace_schema import Environment, GCLResult, GCLTrace


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_trace() -> GCLTrace:
    """Sample trace for testing."""
    return GCLTrace(
        trace_id="gcl-trace-20260718-143052-abc123",
        timestamp=datetime.now(UTC).isoformat(),
        skill="gcp-gce-ops",
        op="DeleteInstance",
        user_request="Delete dev-server-01",
        result=GCLResult.PASS,
        exit_code=0,
        latency_ms=4523,
        iterations_count=2,
        autonomy_ratio=0.75,
        safety_score=1.0,
        safety_failures=0,
        error_type=None,
        degraded_to_human=False,
        degradation_reason=None,
        gcp_project="my-project-123",
        gcp_region="us-central1",
        environment=Environment.PRODUCTION,
    )


@pytest.fixture
def sample_trace_dict(sample_trace: GCLTrace) -> dict[str, Any]:
    """Sample trace as dictionary."""
    return sample_trace.to_dict()


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client."""
    mock = MagicMock()
    return mock


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestUploadTraceToBQ:
    """Tests for upload_trace_to_bq function."""

    def test_upload_success(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify successful upload returns True."""
        # Import here to allow mocking
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            mock_client = MagicMock()
            mock_client.insert_rows_json.return_value = []  # No errors
            mock_bq.Client.return_value = mock_client

            result = upload_trace_to_bq(sample_trace_dict)

            assert result is True
            mock_client.insert_rows_json.assert_called_once()

    def test_upload_failure_returns_false(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify upload failure returns False."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            mock_client = MagicMock()
            mock_client.insert_rows_json.return_value = ["some error"]
            mock_bq.Client.return_value = mock_client

            result = upload_trace_to_bq(sample_trace_dict)

            assert result is False

    def test_upload_google_api_error_returns_false(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify GoogleAPIError is handled gracefully."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            from google.api_core.exceptions import GoogleAPIError

            mock_client = MagicMock()
            mock_client.insert_rows_json.side_effect = GoogleAPIError("API Error")
            mock_bq.Client.return_value = mock_client

            result = upload_trace_to_bq(sample_trace_dict)

            assert result is False

    def test_upload_unexpected_error_returns_false(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify unexpected errors are handled gracefully."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            mock_client = MagicMock()
            mock_client.insert_rows_json.side_effect = RuntimeError("Unexpected error")
            mock_bq.Client.return_value = mock_client

            result = upload_trace_to_bq(sample_trace_dict)

            assert result is False

    def test_upload_uses_correct_table_reference(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify upload uses correct dataset.table reference."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            mock_client = MagicMock()
            mock_client.insert_rows_json.return_value = []
            mock_bq.Client.return_value = mock_client

            upload_trace_to_bq(
                sample_trace_dict,
                dataset_id="custom_dataset",
                table_id="custom_table",
            )

            call_args = mock_client.insert_rows_json.call_args
            table_ref = call_args[0][0]
            assert table_ref == "custom_dataset.custom_table"

    def test_upload_passes_project_id_to_client(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify project_id is passed to BigQuery client."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import upload_trace_to_bq

        with patch("gcl_runner_enhanced.bigquery") as mock_bq:
            mock_client = MagicMock()
            mock_client.insert_rows_json.return_value = []
            mock_bq.Client.return_value = mock_client

            upload_trace_to_bq(sample_trace_dict, project_id="test-project")

            mock_bq.Client.assert_called_once_with(project="test-project")

    def test_bigquery_not_available_returns_false(self, sample_trace_dict: dict[str, Any]) -> None:
        """Verify function handles missing bigquery library gracefully."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

        # Force BIGQUERY_AVAILABLE to False
        with patch("gcl_runner_enhanced.BIGQUERY_AVAILABLE", False):
            # Need to reimport to pick up the patched value
            import importlib
            import gcl_runner_enhanced

            importlib.reload(gcl_runner_enhanced)
            from gcl_runner_enhanced import upload_trace_to_bq

            result = upload_trace_to_bq(sample_trace_dict)
            assert result is False


class TestBQConstants:
    """Tests for BigQuery constants."""

    def test_bq_dataset_id_is_correct(self) -> None:
        """Verify BigQuery dataset ID is set correctly."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import BQ_DATASET_ID

        assert BQ_DATASET_ID == "gcp_skills_gcl_audit"

    def test_bq_table_id_is_correct(self) -> None:
        """Verify BigQuery table ID is set correctly."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from gcl_runner_enhanced import BQ_TABLE_ID

        assert BQ_TABLE_ID == "gcl_traces"


# ── Run Tests ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])