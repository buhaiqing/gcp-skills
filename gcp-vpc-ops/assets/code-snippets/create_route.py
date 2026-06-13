#!/usr/bin/env python3
# create_route.py — Create a VPC route via Python SDK
# Usage: python3 create_route.py

import os

from google.cloud import compute_v1
from google.cloud.compute_v1 import types

project = os.environ["CLOUDSDK_CORE_PROJECT"]
route_client = compute_v1.RoutesClient()

route = types.Route()
route.name = os.environ.get("VPC_ROUTE_NAME", "my-route")
route.destination_range = os.environ.get("VPC_ROUTE_DEST", "0.0.0.0/0")
route.priority = int(os.environ.get("VPC_ROUTE_PRIORITY", "1000"))
route.network = (
    f"https://www.googleapis.com/compute/v1/projects/{project}"
    f"/global/networks/{os.environ.get('VPC_NETWORK_NAME', 'default')}"
)

if next_hop := os.environ.get("VPC_NEXT_HOP_GATEWAY"):
    route.next_hop_gateway = next_hop
elif next_hop := os.environ.get("VPC_NEXT_HOP_INSTANCE"):
    route.next_hop_instance = (
        f"https://www.googleapis.com/compute/v1/projects/{project}"
        f"/zones/{os.environ.get('CLOUDSDK_COMPUTE_ZONE', 'us-central1-a')}"
        f"/instances/{next_hop}"
    )
elif next_hop := os.environ.get("VPC_NEXT_HOP_VPN"):
    route.next_hop_vpn_tunnel = next_hop
elif next_hop := os.environ.get("VPC_NEXT_HOP_IP"):
    route.next_hop_ip = next_hop
else:
    raise ValueError("A next hop (gateway/instance/VPN/IP) must be provided")

op = route_client.insert(project=project, route_resource=route)
print(f"Route creation operation: {op.name}")

op.result()  # blocks until done
print(f"Route {route.name} created successfully")
