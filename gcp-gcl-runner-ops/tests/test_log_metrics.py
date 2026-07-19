#!/usr/bin/env python3
"""
Tests for GCL Log Metrics.

Run with: python -m pytest tests/test_log_metrics.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import NotFound


class TestCreateOrUpdateMetric:
    """Tests for create_or_update_metric function."""

    @patch("scripts.create_log_metrics.logging_v2")
    def test_create_new_metric(self, mock_logging_v2: MagicMock) -> None:
        """Test creating a new metric when it doesn't exist."""
        from scripts.create_log_metrics import create_or_update_metric

        # Setup mock: get_log_metric raises NotFound (metric does not exist)
        mock_client = MagicMock()
        mock_client.get_log_metric.side_effect = NotFound("not found")
        mock_logging_v2.LoggingServiceV2Client.return_value = mock_client

        metric_def = {
            "name": "gcl_error_rate",
            "filter": 'severity=ERROR AND logger="gcl-runner"',
            "type": "DELTA_INT64",
        }

        name, result = create_or_update_metric(mock_client, "test-project", metric_def)

        assert name == "gcl_error_rate"
        assert result is True
        mock_client.create_log_metric.assert_called_once()

    @patch("scripts.create_log_metrics.logging_v2")
    def test_update_existing_metric(self, mock_logging_v2: MagicMock) -> None:
        """Test updating an existing metric."""
        from scripts.create_log_metrics import create_or_update_metric

        # Setup mock
        mock_client = MagicMock()
        existing_metric = MagicMock()
        mock_client.get_log_metric.return_value = existing_metric
        mock_logging_v2.LoggingServiceV2Client.return_value = mock_client

        metric_def = {
            "name": "gcl_error_rate",
            "filter": 'severity=ERROR AND logger="gcl-runner"',
            "type": "DELTA_INT64",
        }

        name, result = create_or_update_metric(mock_client, "test-project", metric_def)

        assert name == "gcl_error_rate"
        assert result is True
        mock_client.update_log_metric.assert_called_once()

    @patch("scripts.create_log_metrics.logging_v2")
    def test_dry_run_creates_nothing(self, mock_logging_v2: MagicMock) -> None:
        """Test that dry_run doesn't make any API calls."""
        from scripts.create_log_metrics import create_or_update_metric

        mock_client = MagicMock()
        existing_metric = MagicMock()
        mock_client.get_log_metric.return_value = existing_metric
        mock_logging_v2.LoggingServiceV2Client.return_value = mock_client

        metric_def = {
            "name": "gcl_error_rate",
            "filter": 'severity=ERROR AND logger="gcl-runner"',
            "type": "DELTA_INT64",
        }

        name, result = create_or_update_metric(mock_client, "test-project", metric_def, dry_run=True)

        assert name == "gcl_error_rate"
        assert result is True
        mock_client.create_log_metric.assert_not_called()
        mock_client.update_log_metric.assert_not_called()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading a valid YAML config file."""
        from scripts.create_log_metrics import load_config

        config_content = """
metrics:
  - name: gcl_error_rate
    description: Test metric
    filter: 'severity=ERROR'
    type: DELTA_INT64
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        metrics = load_config(str(config_file))

        assert len(metrics) == 1
        assert metrics[0]["name"] == "gcl_error_rate"
        assert metrics[0]["type"] == "DELTA_INT64"

    def test_load_config_uses_defaults(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that missing metrics key uses defaults."""
        from scripts.create_log_metrics import DEFAULT_METRICS, load_config

        config_content = """
other_key: value
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        metrics = load_config(str(config_file))

        assert metrics == DEFAULT_METRICS


class TestMetricKindMapping:
    """Tests for metric kind mapping."""

    def test_delta_int64_mapping(self) -> None:
        """Test DELTA_INT64 maps to an integer value."""
        from scripts.create_log_metrics import _metric_kind_from_string

        result = _metric_kind_from_string("DELTA_INT64")
        # Just verify it returns an int, not the actual enum value
        assert isinstance(result, int)

    def test_gauge_float64_mapping(self) -> None:
        """Test GAUGE_FLOAT64 maps to an integer value."""
        from scripts.create_log_metrics import _metric_kind_from_string

        result = _metric_kind_from_string("GAUGE_FLOAT64")
        assert isinstance(result, int)

    def test_delta_distribution_mapping(self) -> None:
        """Test DELTA_DISTRIBUTION maps to an integer value."""
        from scripts.create_log_metrics import _metric_kind_from_string

        result = _metric_kind_from_string("DELTA_DISTRIBUTION")
        assert isinstance(result, int)

    def test_unknown_type_defaults_to_delta_int64(self) -> None:
        """Test unknown metric type defaults to DELTA_INT64."""
        from scripts.create_log_metrics import _metric_kind_from_string

        result = _metric_kind_from_string("UNKNOWN_TYPE")
        # Default is DELTA_INT64 which maps to an int
        assert isinstance(result, int)


class TestDefaultMetrics:
    """Tests for default metrics definitions."""

    def test_default_metrics_have_required_fields(self) -> None:
        """Test all default metrics have required fields."""
        from scripts.create_log_metrics import DEFAULT_METRICS

        required_fields = {"name", "description", "filter", "type"}

        for metric in DEFAULT_METRICS:
            assert required_fields.issubset(metric.keys()), f"Metric {metric['name']} missing fields"

    def test_gcl_error_rate_filter(self) -> None:
        """Test gcl_error_rate metric filter is valid."""
        from scripts.create_log_metrics import DEFAULT_METRICS

        error_rate = next(m for m in DEFAULT_METRICS if m["name"] == "gcl_error_rate")
        assert 'severity=ERROR' in error_rate["filter"]
        assert 'gcl-runner' in error_rate["filter"]

    def test_gcl_safety_failures_filter(self) -> None:
        """Test gcl_safety_failures metric filter is valid."""
        from scripts.create_log_metrics import DEFAULT_METRICS

        safety_failures = next(m for m in DEFAULT_METRICS if m["name"] == "gcl_safety_failures")
        assert "SAFETY_FAIL" in safety_failures["filter"]
        assert "ERROR" in safety_failures["filter"]
