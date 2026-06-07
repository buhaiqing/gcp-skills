# gcloud — GKE CLI

## Conventions
- Always use `--format=json` for machine-parseable output
- Operations API polling: gcloud built-in waiter (returns when DONE) or `--async` for manual polling
- Location flag: use `--zone` for zonal, `--region` for regional

## Command Map: Clusters

| Goal | gcloud command |
|------|---------------|
| Create (Standard) | `gcloud container clusters create NAME --zone=Z --num-nodes=N --machine-type=T --release-channel=C --format=json` |
| Create (Autopilot) | `gcloud container clusters create-auto NAME --location=L --release-channel=C --format=json` |
| Describe | `gcloud container clusters describe NAME --zone=Z --format=json` |
| List | `gcloud container clusters list --format=json` |
| Update | `gcloud container clusters update NAME --zone=Z [--enable-autoscaling] [--workload-pool=P] --format=json` |
| Upgrade (master) | `gcloud container clusters upgrade NAME --zone=Z --master --cluster-version=V --format=json` |
| Resize | `gcloud container clusters resize NAME --node-pool=NP --num-nodes=N --zone=Z --format=json` |
| Delete | `gcloud container clusters delete NAME --zone=Z --format=json` |
| Get credentials | `gcloud container clusters get-credentials NAME --zone=Z` |

## Command Map: Node Pools

| Goal | gcloud command |
|------|---------------|
| Create | `gcloud container node-pools create NAME --cluster=C --zone=Z --num-nodes=N --machine-type=T --format=json` |
| Describe | `gcloud container node-pools describe NAME --cluster=C --zone=Z --format=json` |
| List | `gcloud container node-pools list --cluster=C --zone=Z --format=json` |
| Update (autoscaling) | `gcloud container clusters update NAME --zone=Z --node-pool=NP --enable-autoscaling --min-nodes=M --max-nodes=X --format=json` |
| Upgrade | `gcloud container clusters upgrade NAME --zone=Z --node-pool=NP --cluster-version=V --format=json` |
| Delete | `gcloud container node-pools delete NAME --cluster=C --zone=Z --format=json` |

## Command Map: Utilities

| Goal | gcloud command |
|------|---------------|
| List operations | `gcloud container operations list --zone=Z --format=json` |
| Describe operation | `gcloud container operations describe OP_NAME --zone=Z --format=json` |
| Get server config | `gcloud container get-server-config --zone=Z --format=json` |
| List usable subnets | `gcloud container clusters list --format="json" | jq '.[].network'` |
| Enable GKE API | `gcloud services enable container.googleapis.com` |

## CLI vs API Coverage

| Operation | gcloud | Notes |
|-----------|--------|-------|
| Create cluster | ✅ | Standard + Autopilot fully covered |
| Describe cluster | ✅ | Full JSON output |
| List clusters | ✅ | |
| Update cluster | ✅ | Features, autoscaling, monitoring |
| Delete cluster | ✅ | |
| Node pool CRUD | ✅ | Fully covered |
| Get credentials | ✅ | kubeconfig generation |
| Backup for GKE | Partial | `gcloud container backup-restore` subcommands |
| VPA/HPA | Partial | Requires kubectl for deep config |
| Config Sync | Partial | Requires Config Management API |