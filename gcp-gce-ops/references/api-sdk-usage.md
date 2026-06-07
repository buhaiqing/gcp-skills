# API & SDK — Compute Engine

## REST API
- Discovery doc: https://compute.googleapis.com/$discovery/rest?version=v1
- Base URL: https://compute.googleapis.com/compute/v1/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| Create instance | POST /projects/{p}/zones/{z}/instances | InstancesClient.Insert() |
| Get instance | GET /projects/{p}/zones/{z}/instances/{i} | InstancesClient.Get() |
| List instances | GET /projects/{p}/zones/{z}/instances | InstancesClient.List() |
| Delete instance | DELETE /projects/{p}/zones/{z}/instances/{i} | InstancesClient.Delete() |
| Start instance | POST /projects/{p}/zones/{z}/instances/{i}/start | InstancesClient.Start() |
| Stop instance | POST /projects/{p}/zones/{z}/instances/{i}/stop | InstancesClient.Stop() |
| Reset instance | POST /projects/{p}/zones/{z}/instances/{i}/reset | InstancesClient.Reset() |
| Create disk | POST /projects/{p}/zones/{z}/disks | DisksClient.Insert() |
| Resize disk | POST /projects/{p}/zones/{z}/disks/{d}/resize | DisksClient.Resize() |
| Create snapshot | POST /projects/{p}/global/snapshots | SnapshotsClient.Insert() |
| Create MIG | POST /projects/{p}/zones/{z}/instanceGroupManagers | InstanceGroupManagersClient.Insert() |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create instance | $.targetLink | Created instance self-link |
| Describe instance | $.{status,id,name,zone,machineType,disks} | Instance details |
| List instances | $.items[].{name,status,zone,machineType} | Instance list |
| Create disk | $.targetLink | Created disk self-link |
| Create snapshot | $.targetLink | Created snapshot self-link |
| Describe MIG | $.{name,targetSize,currentActions} | MIG details |
