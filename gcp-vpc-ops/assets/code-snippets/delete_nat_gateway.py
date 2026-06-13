#!/usr/bin/env python3
# delete_nat_gateway.py — Delete a Cloud NAT gateway via Python SDK
# Usage: python3 delete_nat_gateway.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
region = os.environ.get("CLOUDSDK_COMPUTE_REGION", "us-central1")
router_name = os.environ.get("VPC_ROUTER_NAME", "my-router")
nat_name = os.environ.get("VPC_NAT_NAME", "my-nat")
nats_client = compute_v1.RouterNatsClient()

# Find the NAT in the router
nat_list = nats_client.list(project=project, region=region, router=router_name)
nat = next((item for item in nat_list if item.name == nat_name), None)
if not nat:
    raise ValueError(f"NAT gateway {nat_name} not found on router {router_name}")

print(f"NAT Gateway: {nat.name}")
print(f"Distribution Mode: {nat.natIpAllocateOption}")

# Delete
op = nats_client.delete(
    project=project, region=region, router=router_name, nat=nat_name,
)
op.result()
print(f"Cloud NAT {nat.name} deleted successfully")
