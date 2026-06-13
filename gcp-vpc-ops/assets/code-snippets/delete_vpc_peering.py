#!/usr/bin/env python3
# delete_vpc_peering.py — Delete a VPC peering connection via Python SDK
# Usage: python3 delete_vpc_peering.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
network_name = os.environ.get("VPC_NETWORK_NAME", "my-network")
peering_name = os.environ.get("VPC_PEERING_NAME", "my-peering")
peering_client = compute_v1.NetworksPeeringClient()

# Get peering details
peering = peering_client.get(
    project=project, network=network_name, peering=peering_name,
)
print(f"VPC Peering: {peering.name}")
print(f"Peer Network: {peering.peer_network_email}")
print(f"State: {peering.state}")

# Delete
op = peering_client.delete(
    project=project, network=network_name, peering=peering_name,
)
op.result()
print(f"VPC peering {peering.name} deleted successfully")
