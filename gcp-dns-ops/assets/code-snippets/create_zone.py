#!/usr/bin/env python3
# create_zone.py — Create a managed DNS zone via Python SDK
# Usage: python3 create_zone.py

import os

from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()

zone = dns_v1.ManagedZone(
    name=os.environ.get("DNS_ZONE_NAME", "my-zone"),
    dns_name=os.environ.get("DNS_NAME", "example.com."),
    description=os.environ.get("DNS_ZONE_DESCRIPTION", "Zone created by gcp-skills"),
    visibility=getattr(
        dns_v1.ManagedZone.Visibility,
        os.environ.get("DNS_ZONE_VISIBILITY", "PUBLIC"),
    ),
)

visibility = os.environ.get("DNS_ZONE_VISIBILITY", "PUBLIC")
if visibility == "PRIVATE":
    zone.private_visibility_config = dns_v1.ManagedZone.PrivateVisibilityConfig(
        networks=[dns_v1.ManagedZone.PrivateVisibilityConfig.Network(
            network_url=(
                "https://www.googleapis.com/compute/v1/projects/"
                f"{project}/global/networks/"
                f"{os.environ.get('DNS_VPC_NETWORK', 'default')}"
            )
        )]
    )

parent = f"projects/{project}"
created = client.create_managed_zone(parent=parent, managed_zone=zone)
print(f"Zone created: {created.name}")
print(f"Name servers: {created.name_servers}")
