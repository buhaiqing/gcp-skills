#!/usr/bin/env python3
# delete_instance.py — Delete a GCE VM instance via Python SDK
# Usage: python3 delete_instance.py

import os

from google.cloud import compute_v1

client = compute_v1.InstancesClient()
request = compute_v1.DeleteInstanceRequest(
    project=os.environ["CLOUDSDK_CORE_PROJECT"],
    zone=os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1-a"),
    instance=os.environ.get("GCE_INSTANCE_NAME", "my-instance"),
)
operation = client.delete(request=request)
operation.result(timeout=300)
print(f"Deleted instance: {request.instance}")
