# gcloud — Filestore CLI

## Command Map: Instances

| Goal | gcloud command |
|------|---------------|
| Create instance | gcloud filestore instances create INSTANCE --zone=ZONE --tier=TIER --file-share=name=SHARE,capacity=CAPACITY_TiB --network=name=NETWORK |
| Create (regional) | gcloud filestore instances create INSTANCE --region=REGION --tier=ENTERPRISE --file-share=name=SHARE,capacity=CAPACITY_TiB --network=name=NETWORK |
| Describe | gcloud filestore instances describe INSTANCE --zone=ZONE --format=json |
| Describe (regional) | gcloud filestore instances describe INSTANCE --region=REGION --format=json |
| List | gcloud filestore instances list --zone=ZONE --format=json |
| List (regional) | gcloud filestore instances list --region=REGION --format=json |
| Update labels | gcloud filestore instances update INSTANCE --zone=ZONE --update-labels=K=V |
| Update capacity | gcloud filestore instances update INSTANCE --zone=ZONE --file-share=name=SHARE,capacity=NEW_CAPACITY_TiB |
| Delete instance | gcloud filestore instances delete INSTANCE --zone=ZONE |
| Delete (regional) | gcloud filestore instances delete INSTANCE --region=REGION |
| Restore from backup | gcloud filestore instances restore INSTANCE --zone=ZONE --source-backup=BACKUP --source-backup-region=REGION |
| Promote replica | gcloud filestore instances promote-replica INSTANCE --zone=ZONE |
| Pause replica | gcloud filestore instances pause-replica INSTANCE --zone=ZONE |
| Resume replica | gcloud filestore instances resume-replica INSTANCE --zone=ZONE |

## Command Map: Backups

| Goal | gcloud command |
|------|---------------|
| Create backup | gcloud filestore backups create BACKUP --region=REGION --instance=INSTANCE --instance-zone=ZONE |
| Describe backup | gcloud filestore backups describe BACKUP --region=REGION --format=json |
| List backups | gcloud filestore backups list --region=REGION --format=json |
| Delete backup | gcloud filestore backups delete BACKUP --region=REGION |

## Command Map: Snapshots

| Goal | gcloud command |
|------|---------------|
| Create snapshot | gcloud filestore instances snapshots create SNAPSHOT --instance=INSTANCE --zone=ZONE |
| Describe snapshot | gcloud filestore instances snapshots describe SNAPSHOT --instance=INSTANCE --zone=ZONE --format=json |
| List snapshots | gcloud filestore instances snapshots list --instance=INSTANCE --zone=ZONE --format=json |
| Delete snapshot | gcloud filestore instances snapshots delete SNAPSHOT --instance=INSTANCE --zone=ZONE |

## Command Map: Operations & Locations

| Goal | gcloud command |
|------|---------------|
| List operations | gcloud filestore operations list --zone=ZONE --format=json |
| Describe operation | gcloud filestore operations describe OPERATION --zone=ZONE --format=json |
| List locations | gcloud filestore locations list --format=json |
| List regions | gcloud filestore regions list --format=json |
| List zones | gcloud filestore zones list --format=json |

## Instance Creation Examples

### Basic HDD (Zonal)

```bash
gcloud filestore instances create my-instance \
  --zone=us-central1-a \
  --tier=BASIC_HDD \
  --file-share=name=vol1,capacity=1TiB \
  --network=name=default \
  --format=json
```

### Zonal (Custom Performance)

```bash
gcloud filestore instances create my-zonal-instance \
  --zone=us-central1-a \
  --tier=ZONAL \
  --file-share=name=vol1,capacity=2TiB \
  --network=name=default \
  --performance=max-iops=5000,max-throughput-mibps=500 \
  --format=json
```

### Regional (High Availability)

```bash
gcloud filestore instances create my-regional-instance \
  --region=us-central1 \
  --tier=REGIONAL \
  --file-share=name=vol1,capacity=2TiB \
  --network=name=default \
  --performance=max-iops=5000,max-throughput-mibps=500 \
  --format=json
```

## CLI vs API Coverage

| Operation | gcloud filestore | REST API | Notes |
|-----------|-------------------|----------|-------|
| Instance CRUD | ✅ | ✅ | gcloud preferred |
| Backup CRUD | ✅ | ✅ | gcloud preferred |
| Snapshot CRUD | ✅ | ✅ | gcloud preferred |
| Instance replication | ✅ | ✅ | Promote/pause/resume |
| Performance tuning | ✅ | ✅ | Custom performance |
| CMEK encryption | ✅ | ✅ | --kms-key flags |
