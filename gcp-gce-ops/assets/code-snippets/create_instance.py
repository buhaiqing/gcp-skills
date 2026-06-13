#!/usr/bin/env python3
# create_instance.py — Create a GCE VM instance via Python SDK
# Usage: python3 create_instance.py

import os

from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1-a")
instance_name = os.environ.get("GCE_INSTANCE_NAME", "my-instance")

client = compute_v1.InstancesClient()

# Configure boot disk
boot_disk = compute_v1.AttachedDisk()
boot_disk.boot = True
disk_config = compute_v1.AttachedDiskInitializeParams()
disk_config.source_image = "projects/debian-cloud/global/images/family/debian-12"
disk_config.disk_size_gb = 20
disk_config.disk_type = f"projects/{project}/zones/{zone}/diskTypes/pd-balanced"
boot_disk.initialize_params = disk_config

# Configure network
network_interface = compute_v1.NetworkInterface()
network_interface.name = "default"

# Configure instance
instance = compute_v1.Instance()
instance.name = instance_name
instance.machine_type = f"projects/{project}/zones/{zone}/machineTypes/n2-standard-2"
instance.disks = [boot_disk]
instance.network_interfaces = [network_interface]

request = compute_v1.InsertInstanceRequest(
    project=project, zone=zone, instance_resource=instance)
operation = client.insert(request=request)
operation.result(timeout=300)
print(f"Created instance: {instance_name}")
