#!/usr/bin/env python3
# create_network.py — Create a VPC network via Python SDK
# Usage: python3 create_network.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = compute_v1.NetworksClient()

network = compute_v1.Network()
network.name = os.environ.get("VPC_NETWORK_NAME", "my-network")
network.auto_create_subnetworks = False  # custom-mode
network.routing_config = compute_v1.NetworkRoutingConfig()
network.routing_config.routing_mode = "GLOBAL"

op = client.insert(project=project, network_resource=network)
op.result()  # blocks until done
print(f"Created network: {network.name}")
