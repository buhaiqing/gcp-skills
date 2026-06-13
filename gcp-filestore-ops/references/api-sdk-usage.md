# API & SDK — Filestore

## REST API

- Discovery doc: https://file.googleapis.com/$discovery/rest?version=v1
- Base URL: https://file.googleapis.com/v1/

## Operations Map

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Create instance | POST /v1/projects/{p}/locations/{l}/instances | Instance.create() |
| Get instance | GET /v1/projects/{p}/locations/{l}/instances/{i} | Instance.get() |
| List instances | GET /v1/projects/{p}/locations/{l}/instances | Instance.list() |
| Update instance | PATCH /v1/projects/{p}/locations/{l}/instances/{i} | Instance.update() |
| Delete instance | DELETE /v1/projects/{p}/locations/{l}/instances/{i} | Instance.delete() |
| Create backup | POST /v1/projects/{p}/locations/{r}/backups | Backup.create() |
| Get backup | GET /v1/projects/{p}/locations/{r}/backups/{b} | Backup.get() |
| List backups | GET /v1/projects/{p}/locations/{r}/backups | Backup.list() |
| Delete backup | DELETE /v1/projects/{p}/locations/{r}/backups/{b} | Backup.delete() |
| Create snapshot | POST /v1/projects/{p}/locations/{z}/instances/{i}/snapshots | Snapshot.create() |
| List snapshots | GET /v1/projects/{p}/locations/{z}/instances/{i}/snapshots | Snapshot.list() |
| Delete snapshot | DELETE /v1/projects/{p}/locations/{z}/instances/{i}/snapshots/{s} | Snapshot.delete() |
| Restore instance | POST /v1/projects/{p}/locations/{l}/instances/{i}:restore | Instance.restore() |

## Python SDK Code Snippets

### Install

```bash
pip install google-cloud-filestore
```

### Create Instance

```python
# create_instance.py — REST: POST /v1/projects/{p}/locations/{l}/instances
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = "us-central1-a"
instance_id = "my-instance"

client = filestore_v1.CloudFilestoreManagerClient()
parent = f"projects/{project}/locations/{zone}"

instance = filestore_v1.Instance(
    tier="BASIC_HDD",
    file_shares=[
        filestore_v1.FileShareConfig(
            name="vol1",
            capacity_gb=1024  # 1 TiB
        )
    ],
    networks=[
        filestore_v1.NetworkConfig(
            network="default"
        )
    ]
)

operation = client.create_instance(
    parent=parent,
    instance_id=instance_id,
    instance=instance
)
result = operation.result()
print(f"Created instance: {result.name}")
```

### Describe Instance

```python
# describe_instance.py
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = "us-central1-a"
instance_id = "my-instance"

client = filestore_v1.CloudFilestoreManagerClient()
name = f"projects/{project}/locations/{zone}/instances/{instance_id}"

instance = client.get_instance(name=name)
print(f"Name: {instance.name}")
print(f"Tier: {instance.tier}")
print(f"State: {instance.state}")
print(f"Capacity: {instance.file_shares[0].capacity_gb} GB")
```

### List Instances

```python
# list_instances.py
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = "us-central1-a"

client = filestore_v1.CloudFilestoreManagerClient()
parent = f"projects/{project}/locations/{zone}"

for instance in client.list_instances(parent=parent):
    print(f"{instance.name} ({instance.tier}, {instance.state})")
```

### Update Instance (Resize)

```python
# update_instance.py
import os
from google.cloud import filestore_v1
from google.protobuf import field_mask_pb2

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = "us-central1-a"
instance_id = "my-instance"

client = filestore_v1.CloudFilestoreManagerClient()
name = f"projects/{project}/locations/{zone}/instances/{instance_id}"

# Update capacity
instance = filestore_v1.Instance(
    name=name,
    file_shares=[
        filestore_v1.FileShareConfig(
            name="vol1",
            capacity_gb=2048  # 2 TiB
        )
    ]
)

update_mask = field_mask_pb2.FieldMask(paths=["file_shares"])
operation = client.update_instance(
    instance=instance,
    update_mask=update_mask
)
result = operation.result()
print(f"Updated instance: {result.name}")
```

### Delete Instance

```python
# delete_instance.py
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = "us-central1-a"
instance_id = "my-instance"

client = filestore_v1.CloudFilestoreManagerClient()
name = f"projects/{project}/locations/{zone}/instances/{instance_id}"

operation = client.delete_instance(name=name)
operation.result()
print(f"Deleted instance: {instance_id}")
```

### Create Backup

```python
# create_backup.py — REST: POST /v1/projects/{p}/locations/{r}/backups
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
region = "us-central1"
backup_id = "my-backup"
instance_name = "projects/{project}/locations/{zone}/instances/{instance_id}"

client = filestore_v1.CloudFilestoreManagerClient()
parent = f"projects/{project}/locations/{region}"

backup = filestore_v1.Backup(
    source_instance=instance_name,
    description="Daily backup"
)

operation = client.create_backup(
    parent=parent,
    backup_id=backup_id,
    backup=backup
)
result = operation.result()
print(f"Created backup: {result.name}")
```

### List Backups

```python
# list_backups.py
import os
from google.cloud import filestore_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
region = "us-central1"

client = filestore_v1.CloudFilestoreManagerClient()
parent = f"projects/{project}/locations/{region}"

for backup in client.list_backups(parent=parent):
    print(f"{backup.name} (created: {backup.create_time})")
```

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create/Update instance | $.name, $.tier, $.state | Instance details |
| Describe instance | $.{name,tier,state,capacityGb,network} | Instance metadata |
| List instances | $.instances[].{name,tier,state} | Instance list |
| Create backup | $.name, $.state | Backup details |
| List backups | $.backups[].{name,state,sourceInstance} | Backup list |

> ⚠️ Never output credential values in logs. Python SDK reads credentials from `GOOGLE_APPLICATION_CREDENTIALS` env var automatically (safe).
