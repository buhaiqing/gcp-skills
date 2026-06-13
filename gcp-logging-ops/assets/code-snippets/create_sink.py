#!/usr/bin/env python3
# create_sink.py — Create a Cloud Logging log sink via Python SDK
# Usage: python3 create_sink.py

import os

from google.cloud import logging

client = logging.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
sink = client.sink(
    os.environ.get("LOG_SINK_NAME", "my-sink"),
    filter_=os.environ.get("LOG_FILTER", "severity>=ERROR"),
    destination=(
        "bigquery.googleapis.com/projects/"
        f"{os.environ['CLOUDSDK_CORE_PROJECT']}"
        f"/datasets/{os.environ.get('LOG_SINK_DESTINATION', 'my_dataset')}"
    ),
)
sink.create()
print(f"Created sink: {sink.name}, writerIdentity: {sink.writer_identity}")
