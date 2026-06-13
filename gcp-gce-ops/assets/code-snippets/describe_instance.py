#!/usr/bin/env python3
# describe_instance.py — Describe a GCE VM instance via Python SDK
# Usage: python3 describe_instance.py

import os

from google.cloud import compute_v1

client = compute_v1.InstancesClient()
instance = client.get(
    project=os.environ["CLOUDSDK_CORE_PROJECT"],
    zone=os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1-a"),
    instance=os.environ.get("GCE_INSTANCE_NAME", "my-instance"),
)
print(f"Name: {instance.name}, Status: {instance.status}, Machine: {instance.machine_type}")
