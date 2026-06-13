#!/usr/bin/env python3
# list_zones.py — List managed DNS zones via Python SDK
# Usage: python3 list_zones.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
parent = f"projects/{project}"

for zone in client.list_managed_zones(parent=parent):
    print(f"Zone: {zone.name}, DNS: {zone.dns_name}, Visibility: {zone.visibility}")
