#!/usr/bin/env python3
# describe_zone.py — Describe a managed DNS zone via Python SDK
# Usage: python3 describe_zone.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
zone_name = os.environ.get("DNS_ZONE_NAME", "my-zone")

name = f"projects/{project}/managedZones/{zone_name}"
zone = client.get_managed_zone(name=name)
print(f"Zone: {zone.name}, DNS: {zone.dns_name}, Visibility: {zone.visibility}")
print(f"Name servers: {zone.name_servers}")
