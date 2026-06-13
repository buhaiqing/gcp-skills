#!/usr/bin/env python3
# update_zone.py — Update a managed DNS zone via Python SDK
# Usage: python3 update_zone.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
zone_name = os.environ.get("DNS_ZONE_NAME", "my-zone")

zone = dns_v1.ManagedZone(
    name=zone_name,
    description=os.environ.get("DNS_ZONE_DESCRIPTION", "Updated description"),
)
name = f"projects/{project}/managedZones/{zone_name}"
updated = client.update_managed_zone(name=name, managed_zone=zone)
print(f"Zone updated: {updated.name}")
