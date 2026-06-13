#!/usr/bin/env python3
# delete_vpn_tunnel.py — Delete a VPN tunnel via Python SDK
# Usage: python3 delete_vpn_tunnel.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
region = os.environ.get("CLOUDSDK_COMPUTE_REGION", "us-central1")
tunnel_name = os.environ.get("VPC_VPN_TUNNEL_NAME", "my-tunnel")
tunnel_client = compute_v1.VpnTunnelsClient()

# Get tunnel details before deletion
tunnel = tunnel_client.get(
    project=project, region=region, vpn_tunnel=tunnel_name,
)
print(f"VPN Tunnel: {tunnel.name}")
print(f"Target Gateway: {tunnel.target_vpn_gateway}")
print(f"Peer IP: {tunnel.peer_ip_address}")
print(f"Status: {tunnel.status}")

# Delete
op = tunnel_client.delete(project=project, region=region, vpn_tunnel=tunnel_name)
op.result()
print(f"VPN tunnel {tunnel.name} deleted successfully")
