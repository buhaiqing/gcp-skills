#!/usr/bin/env python3
# create_metric.py — Create a log-based metric via Python SDK
# Usage: python3 create_metric.py

import os

from google.cloud import logging

client = logging.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
metric = client.metric(
    os.environ.get("LOG_METRIC_NAME", "my-metric"),
    filter_=os.environ.get("LOG_FILTER", "severity>=ERROR"),
    description=os.environ.get("LOG_METRIC_DESCRIPTION", "Metric created by gcp-skills"),
)
metric.create()
print(f"Created metric: {metric.name}")
