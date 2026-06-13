#!/usr/bin/env python3
# delete_route.py — Delete a VPC route via Python SDK
# Usage: python3 delete_route.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
route_name = os.environ.get("VPC_ROUTE_NAME", "my-route")
route_client = compute_v1.RoutesClient()

# Get route details
route = route_client.get(project=project, route=route_name)
print(f"Route: {route.name}")
print(f"Destination: {route.destination_range}")
next_hop = (route.next_hop_gateway or route.next_hop_instance
            or route.next_hop_vpn_tunnel or route.next_hop_ip)
print(f"Next hop: {next_hop}")

# Delete
op = route_client.delete(project=project, route=route_name)
op.result()
print(f"Route {route_name} deleted successfully")
