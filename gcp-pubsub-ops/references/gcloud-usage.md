# gcloud — Cloud Pub/Sub CLI

## CLI Convention

This skill uses **`gcloud pubsub`** — part of the Google Cloud SDK — for all Pub/Sub control-plane operations.

| Tool | Primary For | Notes |
|------|-------------|-------|
| **`gcloud pubsub topics`** | Topic CRUD, IAM, publish | Create, describe, list, update, delete, add-iam-policy-binding, publish |
| **`gcloud pubsub subscriptions`** | Subscription CRUD, pull, seek, detach, IAM | Create, describe, list, update, delete, pull, seek, detach, add-iam-policy-binding |
| **`gcloud pubsub snapshots`** | Snapshot CRUD | Create, list, describe, delete |

## Command Map: Topics

| Goal | gcloud command |
|------|---------------|
| Create topic | gcloud pubsub topics create TOPIC --project=P --format=json |
| Describe topic | gcloud pubsub topics describe TOPIC --format=json |
| List topics | gcloud pubsub topics list --project=P --format=json |
| Update retention | gcloud pubsub topics update TOPIC --message-retention-duration=D --format=json |
| Update CMEK | gcloud pubsub topics update TOPIC --kms-key-name=K --format=json |
| Delete topic | gcloud pubsub topics delete TOPIC --quiet |
| Publish message | gcloud pubsub topics publish TOPIC --message=MSG --format=json |
| Publish with attrs | gcloud pubsub topics publish TOPIC --message=MSG --attribute=key=value --format=json |
| List subscriptions | gcloud pubsub topics list-subscriptions TOPIC |
| Add IAM binding | gcloud pubsub topics add-iam-policy-binding TOPIC --member=M --role=R --format=json |
| Remove IAM binding | gcloud pubsub topics remove-iam-policy-binding TOPIC --member=M --role=R --format=json |
| Get IAM policy | gcloud pubsub topics get-iam-policy TOPIC --format=json |

## Command Map: Subscriptions

| Goal | gcloud command |
|------|---------------|
| Create pull subscription | gcloud pubsub subscriptions create SUB --topic=TOPIC --ack-deadline=N --message-retention-duration=D --format=json |
| Create push subscription | gcloud pubsub subscriptions create SUB --topic=TOPIC --push-endpoint=URL --format=json |
| Create with exactly-once | gcloud pubsub subscriptions create SUB --topic=TOPIC --enable-exactly-once-delivery --format=json |
| Create with ordering | gcloud pubsub subscriptions create SUB --topic=TOPIC --enable-message-ordering --format=json |
| Describe subscription | gcloud pubsub subscriptions describe SUB --format=json |
| List subscriptions | gcloud pubsub subscriptions list --project=P --format=json |
| Update ack deadline | gcloud pubsub subscriptions update SUB --ack-deadline=N --format=json |
| Update push endpoint | gcloud pubsub subscriptions update SUB --push-endpoint=URL --format=json |
| Update message retention | gcloud pubsub subscriptions update SUB --message-retention-duration=D --format=json |
| Configure DLQ | gcloud pubsub subscriptions update SUB --dead-letter-topic=DLQ_TOPIC --max-delivery-attempts=N --format=json |
| Configure retry | gcloud pubsub subscriptions update SUB --min-retry-delay=D --max-retry-delay=D --format=json |
| Delete subscription | gcloud pubsub subscriptions delete SUB --quiet |
| Pull messages (auto-ack) | gcloud pubsub subscriptions pull SUB --auto-ack --limit=N --format=json |
| Pull messages (manual ack) | gcloud pubsub subscriptions pull SUB --limit=N --format=json |
| Ack messages | gcloud pubsub subscriptions ack SUB --ack-ids=ID1,ID2 |
| Seek to snapshot | gcloud pubsub subscriptions seek SUB --snapshot=SNAP --format=json |
| Seek to timestamp | gcloud pubsub subscriptions seek SUB --time=TIMESTAMP --format=json |
| Detach subscription | gcloud pubsub subscriptions detach SUB |
| Add IAM binding | gcloud pubsub subscriptions add-iam-policy-binding SUB --member=M --role=R --format=json |
| Remove IAM binding | gcloud pubsub subscriptions remove-iam-policy-binding SUB --member=M --role=R --format=json |
| Get IAM policy | gcloud pubsub subscriptions get-iam-policy SUB --format=json |

## Command Map: Snapshots

| Goal | gcloud command |
|------|---------------|
| Create snapshot | gcloud pubsub snapshots create SNAP --subscription=SUB --format=json |
| List snapshots | gcloud pubsub snapshots list --project=P --format=json |
| Describe snapshot | gcloud pubsub snapshots describe SNAP --format=json |
| Delete snapshot | gcloud pubsub snapshots delete SNAP |

## CLI vs API Coverage

| Operation | gcloud | Notes |
|-----------|--------|-------|
| Topic CRUD | ✅ | Full coverage |
| Subscription CRUD | ✅ | Full coverage |
| Publish | ✅ | Single message; use SDK for batch |
| Pull | ✅ | Limited to CLI output; use SDK for streaming |
| DLQ config | ✅ | Full coverage |
| Retry policy | ✅ | Full coverage |
| Snapshot/seek | ✅ | Full coverage |
| IAM | ✅ | Full coverage |
| Schema management | ✅ | gcloud pubsub schemas |
| Streaming pull | ❌ | SDK only |
| Batch publish | ❌ | SDK only |

## Common Flag Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--project` | GCP project ID | From env or gcloud config |
| `--format` | Output format | table (use json for agents) |
| `--quiet` | Suppress interactive prompts | false |
| `--ack-deadline` | Ack deadline in seconds (10-600) | 10 |
| `--message-retention-duration` | Message retention (10m-7d) | 7d |
| `--expiration-period` | Subscription auto-delete (never or 1d-31d) | never |
| `--max-delivery-attempts` | DLQ max delivery (5-100) | 5 |
| `--min-retry-delay` | Minimum retry backoff | 10s |
| `--max-retry-delay` | Maximum retry backoff | 600s |
| `--push-endpoint` | HTTPS URL for push delivery | — |
| `--enable-exactly-once-delivery` | Enable exactly-once | false |
| `--enable-message-ordering` | Enable per-key ordering | false |
| `--kms-key-name` | CMEK key for encryption | — |
