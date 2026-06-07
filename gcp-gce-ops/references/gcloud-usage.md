# gcloud — Compute Engine CLI

## Conventions
- Always use `--format=json` for machine-parseable output
- Operations API polling: use gcloud built-in waiter (returns when DONE)

## Command Map: Instances

| Goal | gcloud command |
|------|---------------|
| Create | gcloud compute instances create NAME --zone=Z --machine-type=T --image-family=F --image-project=P --format=json |
| Describe | gcloud compute instances describe NAME --zone=Z --format=json |
| List | gcloud compute instances list --filter=status:RUNNING --format=json |
| Delete | gcloud compute instances delete NAME --zone=Z --delete-disks=boot --format=json |
| Start | gcloud compute instances start NAME --zone=Z --format=json |
| Stop | gcloud compute instances stop NAME --zone=Z --format=json |
| Reset | gcloud compute instances reset NAME --zone=Z --format=json |
| Set machine type | gcloud compute instances set-machine-type NAME --zone=Z --machine-type=T --format=json |
| Add metadata | gcloud compute instances add-metadata NAME --zone=Z --metadata=K=V --format=json |
| Attach disk | gcloud compute instances attach-disk NAME --disk=D --zone=Z --format=json |

## Command Map: Disks

| Goal | gcloud command |
|------|---------------|
| Create | gcloud compute disks create NAME --zone=Z --size=S --type=T --format=json |
| Describe | gcloud compute disks describe NAME --zone=Z --format=json |
| List | gcloud compute disks list --format=json |
| Resize | gcloud compute disks resize NAME --zone=Z --size=N --format=json |
| Snapshot | gcloud compute disks snapshot NAME --snapshot-names=S --zone=Z --format=json |
| Delete | gcloud compute disks delete NAME --zone=Z --format=json |

## Command Map: Snapshots & MIGs

| Goal | gcloud command |
|------|---------------|
| Snapshot create | gcloud compute snapshots create NAME --source-disk=D --source-disk-zone=Z --format=json |
| Snapshot describe | gcloud compute snapshots describe NAME --format=json |
| Snapshot delete | gcloud compute snapshots delete NAME --format=json |
| MIG create | gcloud compute instance-groups managed create NAME --template=T --size=N --zone=Z --format=json |
| MIG describe | gcloud compute instance-groups managed describe NAME --zone=Z --format=json |
| MIG resize | gcloud compute instance-groups managed resize NAME --size=N --zone=Z --format=json |
| MIG set-autoscaling | gcloud compute instance-groups managed set-autoscaling NAME --max-num-replicas=N --target-cpu-utilization=0.8 --zone=Z --format=json |
| MIG delete | gcloud compute instance-groups managed delete NAME --zone=Z --format=json |

## CLI vs API Coverage

| Operation | gcloud | Notes |
|-----------|--------|-------|
| All instance CRUD | ✅ | Fully covered |
| All disk CRUD | ✅ | Fully covered |
| All snapshot CRUD | ✅ | Fully covered |
| All MIG CRUD | ✅ | Fully covered |
| Machine images | ✅ | gcloud compute machine-images * |
| Sole-tenant nodes | ✅ | gcloud compute sole-tenancy * |
