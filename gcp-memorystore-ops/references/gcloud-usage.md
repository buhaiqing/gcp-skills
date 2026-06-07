# gcloud Usage — Memorystore for Redis

## Overview

`gcloud redis` is the primary CLI interface for Memorystore for Redis. All commands support `--format=json` for machine parsing.

## Conventions

| Convention | Rule |
|--------|------|
| Output | Always use `--format=json` |
| Project | Set via `CLOUDSDK_CORE_PROJECT` or `--project` |
| Region | Required for all commands via `--region` |
| Memory size | Specified as `NGB` (e.g., `1GB`, `5GB`) |

## Command Map

### Instances

| Operation | Command |
|----------|---------|
| Create | `gcloud redis instances create NAME --region=REGION --memory-size=NGB` |
| Describe | `gcloud redis instances describe NAME --region=REGION` |
| List | `gcloud redis instances list --region=REGION` |
| Update | `gcloud redis instances update NAME --region=REGION --memory-size=NGB` |
| Delete | `gcloud redis instances delete NAME --region=REGION` |
| Export | `gcloud redis instances export NAME --region=REGION GCS_URI` |
| Import | `gcloud redis instances import NAME --region=REGION GCS_URI` |
| Failover | `gcloud redis instances failover NAME --region=REGION` |
| Upgrade | `gcloud redis instances upgrade NAME --region=REGION --redis-version=VERSION` |

### Regions & Zones

| Operation | Command |
|----------|---------|
| List regions | `gcloud redis regions list` |

## CLI vs API Coverage

| Resource | gcloud Coverage | Notes |
|----------|----------------|-------|
| Instances | Full | create, describe, list, update, delete, export, import, failover, upgrade |
| Operations | Full | `gcloud redis operations list/describe` |
| Regions | Full | `gcloud redis regions list` |