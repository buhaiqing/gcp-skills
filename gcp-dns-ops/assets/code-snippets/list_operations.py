#!/usr/bin/env python3
# list_operations.py — List DNS zone operations via Python SDK
# Usage: python3 list_operations.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZoneOperationsClient()
zone_name = os.environ.get("DNS_ZONE_NAME", "my-zone")

parent = f"projects/{project}/managedZones/{zone_name}"
for op in client.list_managed_zone_operations(parent=parent):
    print(f"Op: {op.id}, Status: {op.status}, Started: {op.start_time}")
