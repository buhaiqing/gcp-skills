# gcloud Usage — Cloud Logging

## Overview

`gcloud logging` is the primary CLI interface for Cloud Logging. All commands support `--format=json` for machine parsing.

## Conventions

| Convention | Rule |
|--------|------|
| Output | Always use `--format=json` |
| Project | Set via `CLOUDSDK_CORE_PROJECT` or `--project` |
| Location | `global` by default; use `--location` for regional buckets |
| Filter | Log filter expression: `resource.type=gce_instance AND severity>=ERROR` |

## Command Map

### Log Entries

| Operation | Command |
|----------|---------|
| Read entries | `gcloud logging read FILTER` |
| Tail entries (stream) | `gcloud logging tail` |
| List log names | `gcloud logging logs list` |
| List log descriptors | `gcloud logging log-types list` |

### Log Buckets

| Operation | Command |
|----------|---------|
| Create | `gcloud logging buckets create NAME --location=LOC` |
| Describe | `gcloud logging buckets describe NAME --location=LOC` |
| List | `gcloud logging buckets list --location=LOC` |
| Update | `gcloud logging buckets update NAME --retention-days=N` |
| Delete | `gcloud logging buckets delete NAME --location=LOC` |
| Undelete | `gcloud logging buckets undelete NAME --location=LOC` |

### Log Views

| Operation | Command |
|----------|---------|
| Create | `gcloud logging views create NAME --bucket=BUCKET --location=LOC` |
| Describe | `gcloud logging views describe NAME --bucket=BUCKET --location=LOC` |
| List | `gcloud logging views list --bucket=BUCKET --location=LOC` |
| Delete | `gcloud logging views delete NAME --bucket=BUCKET --location=LOC` |

### Log Sinks

| Operation | Command |
|----------|---------|
| Create | `gcloud logging sinks create NAME DESTINATION` |
| Describe | `gcloud logging sinks describe NAME` |
| List | `gcloud logging sinks list` |
| Update | `gcloud logging sinks update NAME DESTINATION` |
| Delete | `gcloud logging sinks delete NAME` |

### Log-Based Metrics

| Operation | Command |
|----------|---------|
| Create | `gcloud logging metrics create NAME --log-filter=FILTER` |
| Describe | `gcloud logging metrics describe NAME` |
| List | `gcloud logging metrics list` |
| Delete | `gcloud logging metrics delete NAME` |

### Log Exclusions

| Operation | Command |
|----------|---------|
| Create | `gcloud logging exclusions create NAME --log-filter=FILTER` |
| Describe | `gcloud logging exclusions describe NAME` |
| List | `gcloud logging exclusions list` |
| Update | `gcloud logging exclusions update NAME --log-filter=FILTER` |
| Delete | `gcloud logging exclusions delete NAME` |

## CLI vs API Coverage

| Resource | gcloud Coverage | Notes |
|----------|----------------|-------|
| Log Entries | Full | read, tail, logs list |
| Buckets | Full | create, describe, list, update, delete, undelete |
| Views | Full | create, describe, list, delete |
| Sinks | Full | create, describe, list, update, delete |
| Metrics | Full | create, describe, list, delete (no update) |
| Exclusions | Full | create, describe, list, update, delete |