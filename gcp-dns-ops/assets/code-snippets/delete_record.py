#!/usr/bin/env python3
# delete_record.py — Delete a DNS record-set via Python SDK
# Usage: python3 delete_record.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ChangesClient()
zone_name = os.environ.get("DNS_ZONE_NAME", "my-zone")
zone_path = f"projects/{project}/managedZones/{zone_name}"

rrset = dns_v1.ResourceRecordSet(
    name=os.environ.get("DNS_RECORD_NAME", "www.example.com."),
    type=os.environ.get("DNS_RECORD_TYPE", "A"),
    ttl=int(os.environ.get("DNS_RECORD_TTL", "300")),
    rrdatas=[os.environ.get("DNS_RECORD_DATA", "192.0.2.1")],
)

change = dns_v1.Change(deletions=[rrset])
change = client.create_change(managed_zone=zone_path, change=change)
print(f"Change ID: {change.id}, Status: {change.status}")
