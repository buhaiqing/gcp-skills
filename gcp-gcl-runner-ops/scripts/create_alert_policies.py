#!/usr/bin/env python3
"""
Create GCP Alert Policies for GCL observability.

Usage:
    python3 scripts/create_alert_policies.py --project YOUR_PROJECT_ID
    python3 scripts/create_alert_policies.py --project YOUR_PROJECT_ID --dry-run
    python3 scripts/create_alert_policies.py --project YOUR_PROJECT_ID --notification-channel CHANNEL_ID
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

# Alert policy definitions for GCL observability
GCL_ALERT_POLICIES = [
    {
        "name": "gcl_error_rate_high",
        "display_name": "GCL Error Rate High",
        "description": "Alert when GCL error rate exceeds 10 errors/minute for 5 minutes",
        "metric": "logging.googleapis.com/gcl_error_rate",
        "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
        "comparison": "COMPARISON_GT",
        "threshold_value": 10,
        "duration": "300s",  # 5 minutes
        "aggregation": {
            "alignment_period": "60s",
            "per_series_aligner": "ALIGN_RATE",
        },
        "severity": "WARNING",
        "documentation_link": "https://github.com/example/gcp-skills/blob/main/gcp-gcl-runner-ops/docs/LOG_METRICS.md",
    },
    {
        "name": "gcl_safety_failure",
        "display_name": "GCL Safety Failure",
        "description": "Alert when any safety failure is detected in GCL execution",
        "metric": "logging.googleapis.com/gcl_safety_failures",
        "filter": 'metric.type="logging.googleapis.com/gcl_safety_failures"',
        "comparison": "COMPARISON_GT",
        "threshold_value": 0,
        "duration": "60s",  # 1 minute - any safety failure is critical
        "aggregation": {
            "alignment_period": "60s",
            "per_series_aligner": "ALIGN_SUM",
        },
        "severity": "CRITICAL",
        "documentation_link": "https://github.com/example/gcp-skills/blob/main/gcp-gcl-runner-ops/docs/LOG_METRICS.md",
    },
    {
        "name": "gcl_latency_high",
        "display_name": "GCL Latency High",
        "description": "Alert when P95 GCL execution latency exceeds 30 seconds for 5 minutes",
        "metric": "logging.googleapis.com/gcl_execution_latency",
        "filter": 'metric.type="logging.googleapis.com/gcl_execution_latency"',
        "comparison": "COMPARISON_GT",
        "threshold_value": 30000,  # 30 seconds in milliseconds
        "duration": "300s",  # 5 minutes
        "aggregation": {
            "alignment_period": "60s",
            "per_series_aligner": "ALIGN_PERCENTILE_95",
        },
        "severity": "WARNING",
        "documentation_link": "https://github.com/example/gcp-skills/blob/main/gcp-gcl-runner-ops/docs/LOG_METRICS.md",
    },
    {
        "name": "gcl_autonomy_degraded",
        "display_name": "GCL Autonomy Degraded",
        "description": "Alert when GCL autonomy ratio falls below 0.5 for 10 minutes",
        "metric": "logging.googleapis.com/gcl_autonomy_ratio",
        "filter": 'metric.type="logging.googleapis.com/gcl_autonomy_ratio"',
        "comparison": "COMPARISON_LT",
        "threshold_value": 0.5,
        "duration": "600s",  # 10 minutes
        "aggregation": {
            "alignment_period": "60s",
            "per_series_aligner": "ALIGN_MEAN",
        },
        "severity": "WARNING",
        "documentation_link": "https://github.com/example/gcp-skills/blob/main/gcp-gcl-runner-ops/docs/LOG_METRICS.md",
    },
]


@dataclass
class AlertPolicyCondition:
    """Represents a single condition in an alert policy."""

    display_name: str
    filter: str
    comparison: str
    threshold_value: float | int
    duration: str
    aggregation: dict[str, str]


@dataclass
class AlertPolicy:
    """Represents a GCP monitoring alert policy."""

    name: str
    display_name: str
    description: str
    conditions: list[AlertPolicyCondition]
    severity: str
    documentation_link: str


def build_condition(condition_def: dict[str, Any]) -> AlertPolicyCondition:
    """Build an AlertPolicyCondition from a definition dict."""
    return AlertPolicyCondition(
        display_name=condition_def["display_name"],
        filter=condition_def["filter"],
        comparison=condition_def["comparison"],
        threshold_value=condition_def["threshold_value"],
        duration=condition_def["duration"],
        aggregation=condition_def["aggregation"],
    )


def build_alert_policy(policy_def: dict[str, Any]) -> AlertPolicy:
    """Build an AlertPolicy from a definition dict."""
    return AlertPolicy(
        name=policy_def["name"],
        display_name=policy_def["display_name"],
        description=policy_def["description"],
        conditions=[build_condition(policy_def)],
        severity=policy_def["severity"],
        documentation_link=policy_def["documentation_link"],
    )


def policy_to_dict(policy: AlertPolicy, notification_channel: str | None = None) -> dict[str, Any]:
    """Convert an AlertPolicy to a dict for the GCP Monitoring API."""
    alert_policy = {
        "display_name": policy.display_name,
        "conditions": [
            {
                "display_name": cond.display_name,
                "condition_threshold": {
                    "filter": cond.filter,
                    "comparison": cond.comparison,
                    "threshold_value": cond.threshold_value,
                    "duration": cond.duration,
                    "aggregation": cond.aggregation,
                },
            }
            for cond in policy.conditions
        ],
        "alert_strategy": {
            "notification_channel_names": [notification_channel] if notification_channel else [],
        },
        "documentation": {
            "content": f"Documentation: {policy.documentation_link}",
            "mime_type": "text/markdown",
        },
        "combining_op": "OR",  # Alert if any condition is met
    }
    return alert_policy


def create_alert_policy(
    monitoring_client: Any,
    project_id: str,
    policy: AlertPolicy,
    notification_channel: str | None = None,
    dry_run: bool = False,
) -> tuple[str, bool]:
    """
    Create an alert policy in GCP Monitoring.

    Returns:
        Tuple of (policy_name, created_successfully)
    """
    policy_dict = policy_to_dict(policy, notification_channel)

    if dry_run:
        print(f"[DRY RUN] Would create policy: {policy.display_name}")
        print(f"  Policy definition: {json.dumps(policy_dict, indent=2)}")
        return policy.name, True

    try:
        request = {"parent": f"projects/{project_id}", "alert_policy": policy_dict}
        response = monitoring_client.create_alert_policy(request=request)
        policy_name = response.name
        print(f"[OK] Created alert policy: {policy.display_name} ({policy_name})")
        return policy_name, True
    except Exception as e:
        print(f"[ERROR] Failed to create policy {policy.display_name}: {e}")
        return policy.name, False


def list_existing_policies(monitoring_client: Any, project_id: str) -> dict[str, str]:
    """List existing alert policies and return a dict of name -> policy_name."""
    request = {"parent": f"projects/{project_id}"}
    response = monitoring_client.list_alert_policies(request=request)
    return {p.display_name: p.name for p in response.alert_policies}


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create GCL Alert Policies in GCP Monitoring")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument(
        "--notification-channel",
        help="Notification channel ID for alerts (optional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview policies without creating them",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing policies with matching names",
    )

    args = parser.parse_args()

    # Import here to avoid issues if not installed
    try:
        from google.cloud import monitoring_v3
    except ImportError:
        print("ERROR: google-cloud-monitoring not installed")
        print("Install with: pip install google-cloud-monitoring")
        return 1

    # Build policy objects
    policies = [build_alert_policy(p) for p in GCL_ALERT_POLICIES]

    if args.dry_run:
        print(f"=== DRY RUN: Would create {len(policies)} alert policies ===\n")
        for policy in policies:
            print(f"Policy: {policy.display_name}")
            print(f"  Description: {policy.description}")
            print(f"  Severity: {policy.severity}")
            for cond in policy.conditions:
                print(f"  Condition: {cond.display_name}")
                print(f"    Filter: {cond.filter}")
                print(f"    Comparison: {cond.comparison} {cond.threshold_value}")
                print(f"    Duration: {cond.duration}")
                print(f"    Aggregation: {cond.aggregation}")
            print()
        return 0

    # Create monitoring client
    client = monitoring_v3.AlertPolicyServiceClient()

    # List existing policies for update check
    existing = {}
    if args.update:
        existing = list_existing_policies(client, args.project)
        print(f"Found {len(existing)} existing policies\n")

    # Create policies
    success_count = 0
    fail_count = 0

    for policy in policies:
        policy_name, ok = create_alert_policy(
            client,
            args.project,
            policy,
            args.notification_channel,
            dry_run=args.dry_run,
        )
        if ok:
            success_count += 1
        else:
            fail_count += 1

    print("\n=== Summary ===")
    print(f"Created: {success_count}")
    print(f"Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
