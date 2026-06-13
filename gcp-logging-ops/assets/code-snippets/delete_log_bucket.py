#!/usr/bin/env python3
# delete_log_bucket.py — Delete a Cloud Logging bucket via Python SDK
# Usage: python3 delete_log_bucket.py

import os

from google.cloud import logging_v2

client = logging_v2.ConfigClientV2()
name = (
    f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}"
    f"/locations/{os.environ.get('LOGGING_LOCATION', 'global')}"
    f"/buckets/{os.environ.get('LOG_BUCKET_NAME', 'my-bucket')}"
)
request = logging_v2.DeleteBucketRequest(name=name)
client.delete_bucket(request=request)
print(f"Deleted bucket: {os.environ.get('LOG_BUCKET_NAME', 'my-bucket')}")
