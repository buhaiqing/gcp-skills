#!/usr/bin/env python3
# create_log_bucket.py — Create a Cloud Logging bucket via Python SDK
# Usage: python3 create_log_bucket.py

import os

from google.cloud import logging_v2

client = logging_v2.ConfigClientV2()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('LOGGING_LOCATION', 'global')}"
bucket = logging_v2.LogBucket(
    retention_days=30, description="Log bucket created by gcp-skills",
)
request = logging_v2.CreateBucketRequest(
    parent=parent,
    bucket_id=os.environ.get("LOG_BUCKET_NAME", "my-bucket"),
    bucket=bucket,
)
response = client.create_bucket(request=request)
print(f"Created bucket: {response.name}")
