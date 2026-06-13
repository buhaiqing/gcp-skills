#!/usr/bin/env python3
# list_log_entries.py — List Cloud Logging entries via Python SDK
# Usage: python3 list_log_entries.py

import os

from google.cloud import logging

client = logging.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
filter_str = os.environ.get("LOG_FILTER", "severity>=ERROR")
entries = client.list_entries(filter_=filter_str, page_size=50)
for entry in entries:
    print(f"[{entry.timestamp}] {entry.log_name}: {entry.payload}")
