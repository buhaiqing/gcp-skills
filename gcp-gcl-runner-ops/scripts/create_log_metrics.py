#!/usr/bin/env python3
"""
Create Cloud Logging log-based metrics for GCL observability.

Usage:
    python3 scripts/create_log_metrics.py [--project PROJECT_ID] [--dry-run]

Prerequisites:
    pip install google-cloud-logging pyyaml

Exit codes:
    0 = SUCCESS, 1 = ERROR, 2 = DRY_RUN (no changes)
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import yaml
from google.api import metric_pb2
from google.api_core.exceptions import NotFound
from google.cloud import logging_v2
from google.cloud.logging_v2.services.logging_service_v2 import LoggingServiceV2Client
from google.cloud.logging_v2.types import LogMetric

# ── Metric Definitions ────────────────────────────────────────────────────────

DEFAULT_METRICS: list[dict[str, Any]] = [
    {
        "name": "gcl_error_rate",
        "description": "Rate of GCL errors (ERROR/WARNING logs per minute)",
        "filter": "severity=ERROR AND logger=\"gcl-runner\"",
        "type": "DELTA_INT64",
    },
    {
        "name": "gcl_execution_latency",
        "description": "GCL execution latency histogram from trace logs",
        "filter": "logger=\"gcl-runner\" AND \"latency_ms\" IN elements(message)",
        "type": "DELTA_DISTRIBUTION",
    },
    {
        "name": "gcl_safety_failures",
        "description": "Count of safety=0 events in GCL execution",
        "filter": "severity=ERROR AND 'SAFETY_FAIL' IN elements(message)",
        "type": "DELTA_INT64",
    },
    {
        "name": "gcl_autonomy_ratio",
        "description": "Average autonomy ratio from GCL trace logs",
        "filter": "logger=\"gcl-runner\" AND \"autonomy_ratio\" IN elements(message)",
        "type": "GAUGE_FLOAT64",
    },
]


# ── Core Logic ────────────────────────────────────────────────────────────────


def load_config(config_path: str) -> list[dict[str, Any]]:
    """Load metric definitions from YAML config file."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("metrics", DEFAULT_METRICS)


def _metric_kind_from_string(metric_type: str) -> int:
    """Map string metric type to MetricKind enum value.

    MetricKind values from google.api.metric_pb2.MetricDescriptor:
    - GAUGE = 1
    - DELTA = 2
    - CUMULATIVE = 3
    """
    mapping = {
        "GAUGE_INT64": metric_pb2.MetricDescriptor.MetricKind.GAUGE,
        "GAUGE_FLOAT64": metric_pb2.MetricDescriptor.MetricKind.GAUGE,
        "GAUGE_DISTRIBUTION": metric_pb2.MetricDescriptor.MetricKind.GAUGE,
        "DELTA_INT64": metric_pb2.MetricDescriptor.MetricKind.DELTA,
        "DELTA_FLOAT64": metric_pb2.MetricDescriptor.MetricKind.DELTA,
        "DELTA_DISTRIBUTION": metric_pb2.MetricDescriptor.MetricKind.DELTA,
    }
    return mapping.get(metric_type, metric_pb2.MetricDescriptor.MetricKind.DELTA)


def create_or_update_metric(
    client: LoggingServiceV2Client,
    project_id: str,
    metric_def: dict[str, Any],
    dry_run: bool = False,
) -> tuple[str, bool]:
    """
    Create or update a log metric.

    Returns:
        Tuple of (metric_name, was_created_or_updated)
    """
    metric_name = metric_def["name"]
    full_metric_name = f"projects/{project_id}/metrics/{metric_name}"

    # Check if metric exists
    existing = None
    try:
        existing = client.get_log_metric(request={"metric_name": full_metric_name})
    except NotFound:
        existing = None  # Metric doesn't exist

    if dry_run:
        action = "CREATE" if existing is None else "UPDATE"
        print(f"[DRY-RUN] Would {action} metric: {metric_name}")
        return metric_name, True

    # Build the metric
    metric = LogMetric()
    metric.name = metric_name
    metric.filter = metric_def["filter"]
    metric.description = metric_def.get("description", "")
    metric.metric_descriptor.type = f"logging.googleapis.com/{metric_name}"

    if existing is None:
        client.create_log_metric(request={"parent": f"projects/{project_id}", "metric": metric})
        print(f"Created metric: {metric_name}")
    else:
        client.update_log_metric(request={"metric_name": full_metric_name, "metric": metric})
        print(f"Updated metric: {metric_name}")

    return metric_name, True


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Cloud Logging log metrics for GCL")
    parser.add_argument("--project", default=None, help="GCP project ID (default: from gcloud config)")
    parser.add_argument("--config", default=None, help="Path to metrics config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without making changes")
    args = parser.parse_args()

    # Resolve project
    project_id = args.project
    if not project_id:
        import subprocess
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
        )
        project_id = result.stdout.strip()

    if not project_id:
        print("Error: No project ID specified. Use --project or set gcloud config.", file=sys.stderr)
        return 1

    # Load metrics config
    if args.config:
        metrics = load_config(args.config)
    else:
        metrics = DEFAULT_METRICS

    # Create/update each metric
    client = logging_v2.LoggingServiceV2Client()
    success_count = 0
    error_count = 0

    for metric_def in metrics:
        try:
            _, _ = create_or_update_metric(client, project_id, metric_def, dry_run=args.dry_run)
            success_count += 1
        except Exception as e:
            print(f"Error creating metric {metric_def['name']}: {e}", file=sys.stderr)
            error_count += 1

    print(f"\nSummary: {success_count} succeeded, {error_count} failed")
    if args.dry_run:
        return 2
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
