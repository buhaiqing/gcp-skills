#!/usr/bin/env python3
# list_records.py — List DNS record-sets via Python SDK
# Usage: python3 list_records.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ResourceRecordSetsClient()
zone_name = os.environ.get("DNS_ZONE_NAME", "my-zone")

parent = f"projects/{project}/managedZones/{zone_name}"
for rrset in client.list_resource_record_sets(parent=parent):
    print(f"Name: {rrset.name}, Type: {rrset.type}, TTL: {rrset.ttl}")
    for rd in rrset.rrdatas:
        print(f"  Data: {rd}")
