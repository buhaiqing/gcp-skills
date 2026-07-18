#!/usr/bin/env python3
"""
Tests for GCL Alert Policies.

Run with: python -m pytest tests/test_alert_policies.py -v
"""

from __future__ import annotations

# Import from the scripts module
from scripts.create_alert_policies import (
    GCL_ALERT_POLICIES,
    AlertPolicy,
    AlertPolicyCondition,
    build_alert_policy,
    build_condition,
    policy_to_dict,
)


class TestGCLAlertPolicyDefinitions:
    """Tests for GCL alert policy definitions."""

    def test_all_policies_have_required_fields(self) -> None:
        """Test all policy definitions have required fields."""
        required_fields = {
            "name",
            "display_name",
            "description",
            "metric",
            "filter",
            "comparison",
            "threshold_value",
            "duration",
            "aggregation",
            "severity",
            "documentation_link",
        }

        for policy in GCL_ALERT_POLICIES:
            assert required_fields.issubset(
                policy.keys()
            ), f"Policy {policy['name']} missing fields"

    def test_policy_names_are_valid(self) -> None:
        """Test all policy names follow naming convention."""
        for policy in GCL_ALERT_POLICIES:
            name = policy["name"]
            # Names should be lowercase with underscores
            assert name == name.lower(), f"Policy name {name} should be lowercase"
            assert "_" in name or name.isalpha(), f"Policy name {name} should use underscores or be alphabetic"

    def test_gcl_error_rate_high_threshold(self) -> None:
        """Test gcl_error_rate_high has correct threshold."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_error_rate_high")
        assert policy["threshold_value"] == 10
        assert policy["comparison"] == "COMPARISON_GT"
        assert policy["duration"] == "300s"  # 5 minutes

    def test_gcl_safety_failure_threshold(self) -> None:
        """Test gcl_safety_failure has correct threshold."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_safety_failure")
        assert policy["threshold_value"] == 0
        assert policy["comparison"] == "COMPARISON_GT"
        assert policy["duration"] == "60s"  # 1 minute
        assert policy["severity"] == "CRITICAL"

    def test_gcl_latency_high_threshold(self) -> None:
        """Test gcl_latency_high has correct threshold."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_latency_high")
        assert policy["threshold_value"] == 30000  # 30 seconds in ms
        assert policy["comparison"] == "COMPARISON_GT"
        assert policy["duration"] == "300s"  # 5 minutes
        assert policy["aggregation"]["per_series_aligner"] == "ALIGN_PERCENTILE_95"

    def test_gcl_autonomy_degraded_threshold(self) -> None:
        """Test gcl_autonomy_degraded has correct threshold."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_autonomy_degraded")
        assert policy["threshold_value"] == 0.5
        assert policy["comparison"] == "COMPARISON_LT"  # Less than, not greater than
        assert policy["duration"] == "600s"  # 10 minutes

    def test_all_policies_use_correct_metrics(self) -> None:
        """Test all policies reference correct metric names."""
        expected_metrics = {
            "gcl_error_rate_high": "logging.googleapis.com/gcl_error_rate",
            "gcl_safety_failure": "logging.googleapis.com/gcl_safety_failures",
            "gcl_latency_high": "logging.googleapis.com/gcl_execution_latency",
            "gcl_autonomy_degraded": "logging.googleapis.com/gcl_autonomy_ratio",
        }

        for policy in GCL_ALERT_POLICIES:
            if policy["name"] in expected_metrics:
                expected = expected_metrics[policy["name"]]
                assert policy["metric"] == expected, (
                    f"Policy {policy['name']} metric mismatch: "
                    f"expected {expected}, got {policy['metric']}"
                )


class TestBuildCondition:
    """Tests for build_condition function."""

    def test_build_condition_creates_valid_condition(self) -> None:
        """Test build_condition creates a valid AlertPolicyCondition."""
        condition_def = {
            "display_name": "Error rate > 10/min",
            "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 10,
            "duration": "300s",
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_RATE",
            },
        }

        condition = build_condition(condition_def)

        assert isinstance(condition, AlertPolicyCondition)
        assert condition.display_name == "Error rate > 10/min"
        assert condition.threshold_value == 10
        assert condition.duration == "300s"


class TestBuildAlertPolicy:
    """Tests for build_alert_policy function."""

    def test_build_alert_policy_creates_valid_policy(self) -> None:
        """Test build_alert_policy creates a valid AlertPolicy."""
        policy_def = GCL_ALERT_POLICIES[0]  # Use first policy definition

        policy = build_alert_policy(policy_def)

        assert isinstance(policy, AlertPolicy)
        assert policy.name == policy_def["name"]
        assert policy.display_name == policy_def["display_name"]
        assert len(policy.conditions) == 1
        assert policy.severity == policy_def["severity"]


class TestPolicyToDict:
    """Tests for policy_to_dict function."""

    def test_policy_to_dict_includes_required_fields(self) -> None:
        """Test policy_to_dict includes all required API fields."""
        policy_def = {
            "name": "gcl_error_rate_high",
            "display_name": "GCL Error Rate High",
            "description": "Alert when error rate > 10/min",
            "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 10,
            "duration": "300s",
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_RATE",
            },
            "severity": "WARNING",
            "documentation_link": "https://example.com/docs",
        }

        policy = build_alert_policy(policy_def)
        result = policy_to_dict(policy)

        assert "display_name" in result
        assert "conditions" in result
        assert "combining_op" in result
        assert "documentation" in result

    def test_policy_to_dict_condition_format(self) -> None:
        """Test policy_to_dict condition format is correct."""
        policy_def = {
            "name": "gcl_error_rate_high",
            "display_name": "GCL Error Rate High",
            "description": "Alert when error rate > 10/min",
            "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 10,
            "duration": "300s",
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_RATE",
            },
            "severity": "WARNING",
            "documentation_link": "https://example.com/docs",
        }

        policy = build_alert_policy(policy_def)
        result = policy_to_dict(policy)

        condition = result["conditions"][0]
        assert "display_name" in condition
        assert "condition_threshold" in condition
        threshold = condition["condition_threshold"]
        assert threshold["filter"] == policy_def["filter"]
        assert threshold["comparison"] == "COMPARISON_GT"
        assert threshold["threshold_value"] == 10
        assert threshold["duration"] == "300s"

    def test_policy_to_dict_with_notification_channel(self) -> None:
        """Test policy_to_dict includes notification channel when provided."""
        policy_def = {
            "name": "gcl_error_rate_high",
            "display_name": "GCL Error Rate High",
            "description": "Alert when error rate > 10/min",
            "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 10,
            "duration": "300s",
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_RATE",
            },
            "severity": "WARNING",
            "documentation_link": "https://example.com/docs",
        }

        policy = build_alert_policy(policy_def)
        result = policy_to_dict(policy, notification_channel="channel-123")

        assert result["alert_strategy"]["notification_channel_names"] == ["channel-123"]

    def test_policy_to_dict_without_notification_channel(self) -> None:
        """Test policy_to_dict handles missing notification channel."""
        policy_def = {
            "name": "gcl_error_rate_high",
            "display_name": "GCL Error Rate High",
            "description": "Alert when error rate > 10/min",
            "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
            "comparison": "COMPARISON_GT",
            "threshold_value": 10,
            "duration": "300s",
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_RATE",
            },
            "severity": "WARNING",
            "documentation_link": "https://example.com/docs",
        }

        policy = build_alert_policy(policy_def)
        result = policy_to_dict(policy, notification_channel=None)

        assert result["alert_strategy"]["notification_channel_names"] == []


class TestAlertPolicyThresholds:
    """Tests for verifying specific threshold values."""

    def test_error_rate_threshold_is_10_per_minute(self) -> None:
        """Verify error rate threshold is 10 per minute."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_error_rate_high")
        assert policy["threshold_value"] == 10
        # Rate per minute with 5 min window = 50 total
        # But threshold is per minute aligned
        assert policy["aggregation"]["per_series_aligner"] == "ALIGN_RATE"

    def test_safety_failure_threshold_is_zero(self) -> None:
        """Verify safety failure triggers on any occurrence."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_safety_failure")
        assert policy["threshold_value"] == 0
        # Any safety failure should trigger immediately
        assert policy["duration"] == "60s"

    def test_latency_threshold_is_30_seconds(self) -> None:
        """Verify latency threshold is 30 seconds (30000 ms)."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_latency_high")
        assert policy["threshold_value"] == 30000  # 30 seconds in ms
        assert policy["aggregation"]["per_series_aligner"] == "ALIGN_PERCENTILE_95"

    def test_autonomy_threshold_is_0_5(self) -> None:
        """Verify autonomy threshold is 0.5 (50%)."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_autonomy_degraded")
        assert policy["threshold_value"] == 0.5
        # COMPARISON_LT because we alert when autonomy drops BELOW threshold
        assert policy["comparison"] == "COMPARISON_LT"
        # 10 minute window to confirm sustained degradation
        assert policy["duration"] == "600s"


class TestPolicyDuration:
    """Tests for alert policy durations."""

    def test_error_rate_duration_is_5_minutes(self) -> None:
        """Test error rate alert waits 5 minutes before triggering."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_error_rate_high")
        assert policy["duration"] == "300s"  # 5 minutes in seconds

    def test_safety_failure_duration_is_1_minute(self) -> None:
        """Test safety failure triggers quickly (1 minute)."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_safety_failure")
        assert policy["duration"] == "60s"  # 1 minute - critical issue

    def test_latency_duration_is_5_minutes(self) -> None:
        """Test latency alert waits 5 minutes before triggering."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_latency_high")
        assert policy["duration"] == "300s"  # 5 minutes

    def test_autonomy_duration_is_10_minutes(self) -> None:
        """Test autonomy alert waits 10 minutes before triggering."""
        policy = next(p for p in GCL_ALERT_POLICIES if p["name"] == "gcl_autonomy_degraded")
        assert policy["duration"] == "600s"  # 10 minutes
