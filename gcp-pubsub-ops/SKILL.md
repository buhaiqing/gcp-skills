---
name: gcp-pubsub-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Pub/Sub resources — topics, subscriptions, messages, dead-letter topics,
  retry policies, snapshots, IAM, and backlog diagnostics. User mentions Cloud
  Pub/Sub, Pub/Sub, topic, subscription, message, publish, pull, push, dead-letter,
  DLQ, snapshot, or describes messaging scenarios (e.g., "create a topic", "messages
  stuck", "set up dead-letter queue", "replay from snapshot") even without naming the
  product directly. Not for Cloud Storage, Cloud SQL, BigQuery, or other storage/data
  products that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud` including `gcloud pubsub` module), Python SDK
  (`google-cloud-pubsub`), Go SDK (`cloud.google.com/go/pubsub`), valid service
  account credentials with Pub/Sub Admin or Editor IAM roles, network access to
  Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-08"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://pubsub.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud pubsub topics --help and gcloud pubsub subscriptions --help confirm
    subcommands: topics (create, describe, list, update, delete, iam), subscriptions
    (create, describe, list, update, delete, seek, detach, iam), snapshots (create,
    list, describe, delete). See https://cloud.google.com/sdk/gcloud/reference/pubsub
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Pub/Sub Operations Skill

## Overview

Cloud Pub/Sub is a fully-managed real-time messaging service for event-driven systems and streaming analytics. This skill uses a **dual-path CLI approach**: `gcloud pubsub` for control-plane ops. Python SDK and JIT Go SDK are documented in references.

> **UX Compliance**: Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### Core Standards

| # | Standard | How Fulfilled |
|---|----------|---------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise triggers and delegation rules |
| 2 | **Structured I/O** | `{{env.*}}`, `{{user.*}}`, `{{output.*}}` with documented types |
| 3 | **Explicit Steps** | Pre-flight → Execute → Validate → Recover for each operation |
| 4 | **Failure Strategies** | Error taxonomy (≥10 codes), HALT vs retry logic |
| 5 | **Single Responsibility** | Pub/Sub only; delegation to IAM, Monitoring, Logging skills |

### Google Cloud Architecture Framework

| Pillar | Reference |
|--------|-----------|
| **Security** | IAM roles, push authentication, CMEK encryption, VPC-SC |
| **Stability** | Dead-letter topics, retry policies, snapshot/seek, backlog monitoring |
| **Cost** | Message volume tracking, egress costs, DLQ overflow prevention |
| **Efficiency** | Batch publish/pull, ordering keys, exactly-once delivery |
| **Performance** | Regional endpoints, streaming pull, push vs pull delivery |

Full details: [references/well-architected-assessment.md](references/well-architected-assessment.md)

## Trigger & Scope

### SHOULD Use When
- User mentions "Cloud Pub/Sub", "Pub/Sub", "topic", "subscription", "message", "publish", "pull", "push", "dead-letter", "DLQ", "snapshot"
- Task: topic CRUD, subscription CRUD, message publish/pull, dead-letter config, retry policy, snapshot/seek, IAM, backlog diagnostics

### SHOULD NOT Use When
- Cloud Storage → `gcp-gcs-ops`; Cloud SQL → `gcp-cloudsql-ops`; BigQuery → `gcp-bigquery-ops`
- IAM/SA → `gcp-iam-ops`; Monitoring → `gcp-monitoring-ops`
- Console-only flows with no API

## Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Access token | NEVER ask; refresh if expired |
| `{{user.topic_id}}` | Topic ID | Ask once, reuse |
| `{{user.subscription_id}}` | Subscription ID | Ask once, reuse |
| `{{user.message_data}}` | Message payload | Ask once |
| `{{user.ordering_key}}` | Ordering key for message | Ask once; optional |
| `{{user.dead_letter_topic}}` | Dead-letter topic ID | Ask once; for DLQ config |
| `{{user.max_delivery_attempts}}` | Max delivery attempts | Ask once; default 5 |
| `{{user.ack_deadline_seconds}}` | Ack deadline (10-600) | Ask once; default 10 |
| `{{user.retention_duration}}` | Message retention duration (e.g., 168h, 7d) | Ask once; default 168h |
| `{{user.push_endpoint}}` | Push endpoint URL | Ask once; for push subs |
| `{{user.snapshot_id}}` | Snapshot ID | Ask once, reuse |
| `{{user.member}}` | IAM member (user:xxx, serviceAccount:xxx) | Ask once |
| `{{user.role}}` | IAM role (roles/pubsub.*) | Ask once |
| `{{output.project_number}}` | GCP project number | Parse from `gcloud projects describe` |
| `{{output.*}}` | Previous step result | Parse from API response |

> **Security**: Never output credentials. Mask in logs. Verify with `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key exists"`.

## API Conventions

- **REST API**: Pub/Sub v1 (`pubsub.googleapis.com`). JSON paths centralized in [references/api-sdk-usage.md](references/api-sdk-usage.md).
- **Errors**: HTTP/gRPC → canonical types. See [references/troubleshooting.md](references/troubleshooting.md).
- **Idempotency**: Topic/subscription names are unique per project; ALREADY_EXISTS on duplicate create.

## Prerequisites

### CLI Availability Check

Run this before any operation. Idempotent — installs `gcloud` only if missing:

```bash
if command -v gcloud &>/dev/null; then
  echo "✅ gcloud $(gcloud --version 2>&1 | head -1) already installed"
else
  echo "WARN: gcloud not found — installing Google Cloud SDK..."
  if command -v apt-get &>/dev/null; then
    echo "DIAG: Detected Debian/Ubuntu — installing via apt"
    sudo apt-get update && sudo apt-get install -y google-cloud-cli
  elif command -v yum &>/dev/null; then
    echo "DIAG: Detected RHEL/CentOS — installing via yum"
    sudo yum install -y google-cloud-cli
  elif command -v brew &>/dev/null; then
    echo "DIAG: Detected macOS — installing via Homebrew"
    brew install --cask google-cloud-sdk
  elif command -v python3 &>/dev/null; then
    echo "DIAG: Detected Python — installing via pip"
    python3 -m pip install --upgrade google-cloud-sdk
  else
    echo "ERROR: No supported package manager found"
    echo "FIX: Install Google Cloud SDK manually: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
  echo "RESULT: gcloud installed successfully"
fi

# Ensure pubsub component is available
if ! gcloud pubsub --help &>/dev/null 2>&1; then
  echo "WARN: gcloud pubsub component missing — installing..."
  gcloud components install pubsub-emulator --quiet
fi
```

After installation, verify credentials:
```bash
gcloud auth application-default login  # Interactive browser auth
gcloud config set project "{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Capabilities

| Operation | CLI Tool | Risk |
|-----------|----------|------|
| Create Topic | `gcloud pubsub topics` | Low |
| Describe Topic | `gcloud pubsub topics` | None |
| List Topics | `gcloud pubsub topics` | None |
| Update Topic | `gcloud pubsub topics` | Medium |
| Delete Topic | `gcloud pubsub topics` | **High** |
| Create Subscription | `gcloud pubsub subscriptions` | Low |
| Describe Subscription | `gcloud pubsub subscriptions` | None |
| List Subscriptions | `gcloud pubsub subscriptions` | None |
| Update Subscription | `gcloud pubsub subscriptions` | Medium |
| Delete Subscription | `gcloud pubsub subscriptions` | **High** — in-flight messages lost |
| Publish Message | `gcloud pubsub topics publish` / SDK | Low |
| Pull Message | `gcloud pubsub subscriptions pull` / SDK | None |
| Configure DLQ | `gcloud pubsub subscriptions update` | Medium |
| Configure Retry | `gcloud pubsub subscriptions update` | Medium |
| Create Snapshot | `gcloud pubsub snapshots create` | Low |
| Seek to Snapshot | `gcloud pubsub subscriptions seek` | Medium |
| Set IAM | `gcloud pubsub topics/subscriptions add-iam-policy-binding` | Medium |
| Backlog Diagnostics | Cloud Monitoring metrics | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-08 | Initial release |

## Execution Flows

> All SDK (Python/Go) code snippets are in [references/api-sdk-usage.md](references/api-sdk-usage.md). For detailed CLI variants, see [references/gcloud-usage.md](references/gcloud-usage.md). For error recovery, see [references/troubleshooting.md](references/troubleshooting.md). For idempotent patterns, see [references/idempotency-checklist.md](references/idempotency-checklist.md).

### Create Topic

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic name valid | `^[a-zA-Z][a-zA-Z0-9_-]{0,254}$` | Match | HALT — invalid name |
| Name unique | `gcloud pubsub topics describe "{{user.topic_id}}" --quiet` | NOT_FOUND | HALT — topic exists |

**CLI**: `gcloud pubsub topics create "{{user.topic_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Variants*: `--message-retention-duration=7d`, `--kms-key-name="{{user.kms_key}}"`

**Validate**: `gcloud pubsub topics describe "{{user.topic_id}}" --format="json" | jq '{name, messageRetentionDuration}'`

### Describe Topic

**CLI**: `gcloud pubsub topics describe "{{user.topic_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Extract*: `jq '{name, messageRetentionDuration, kmsKeyName, schemaSettings, subscriptions}'`
*IAM*: `gcloud pubsub topics get-iam-policy "{{user.topic_id}}" --format="json"`

### List Topics

**CLI**: `gcloud pubsub topics list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Filter*: `jq '[.[] | {name: .name, messageRetentionDuration}]'`

### Update Topic

**Pre-flight**: Topic exists.

**CLI**:
- Message retention: `gcloud pubsub topics update "{{user.topic_id}}" --message-retention-duration="{{user.retention_duration:-168h}}" --format="json"`
- CMEK: `gcloud pubsub topics update "{{user.topic_id}}" --kms-key-name="{{user.kms_key}}" --format="json"`

**Validate**: `gcloud pubsub topics describe "{{user.topic_id}}" --format="json" | jq '{name, messageRetentionDuration, kmsKeyName}'`

### Delete Topic

**Pre-flight (Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirms | User types exact topic name `{{user.topic_id}}` | Match | HALT |
| Subscriptions listed | `gcloud pubsub topics list-subscriptions "{{user.topic_id}}"` | Show attached subs | Warn — subscriptions will be detached |

**WARN**: Deleting a topic detaches all subscriptions. In-flight messages may be lost.

**CLI**: `gcloud pubsub topics delete "{{user.topic_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --quiet`

**Validate**: `gcloud pubsub topics describe "{{user.topic_id}}" --quiet 2>&1 || echo "✅ Topic confirmed deleted"`

### Create Subscription

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic exists | `gcloud pubsub topics describe "{{user.topic_id}}" --quiet` | Exit 0 | HALT — create topic first |
| Sub name unique | `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --quiet` | NOT_FOUND | HALT — subscription exists |

**CLI (pull)**: `gcloud pubsub subscriptions create "{{user.subscription_id}}" --topic="{{user.topic_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --ack-deadline="{{user.ack_deadline_seconds:-10}}" --message-retention-duration="{{user.message_retention:-7d}}" --format="json"`
*Variants*: `--enable-exactly-once-delivery`, `--enable-message-ordering`, `--expiration-period=3d`

**CLI (push)**: `gcloud pubsub subscriptions create "{{user.subscription_id}}" --topic="{{user.topic_id}}" --push-endpoint="{{user.push_endpoint}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '{name, topic, ackDeadlineSeconds, pushConfig}'`

### Describe Subscription

**CLI**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Extract*: `jq '{name, topic, ackDeadlineSeconds, messageRetentionDuration, pushConfig, deadLetterPolicy, retryPolicy, expirationPolicy, enableMessageOrdering, enableExactlyOnceDelivery}'`

### List Subscriptions

**CLI**: `gcloud pubsub subscriptions list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Filter by topic*: `gcloud pubsub topics list-subscriptions "{{user.topic_id}}"`
*Filter*: `jq '[.[] | {name: .name, topic: .topic, ackDeadlineSeconds, pushConfig}]'`

### Update Subscription

**Pre-flight**: Subscription exists.

**CLI**:
- Ack deadline: `gcloud pubsub subscriptions update "{{user.subscription_id}}" --ack-deadline="{{user.ack_deadline_seconds}}" --format="json"`
- Push endpoint: `gcloud pubsub subscriptions update "{{user.subscription_id}}" --push-endpoint="{{user.push_endpoint}}" --format="json"`
- Message retention: `gcloud pubsub subscriptions update "{{user.subscription_id}}" --message-retention-duration="{{user.message_retention}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '{ackDeadlineSeconds, messageRetentionDuration, pushConfig}'`

### Delete Subscription

**Pre-flight (Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirms | User types exact subscription name `{{user.subscription_id}}` | Match | HALT |
| Backlog size | `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format=json | jq -r '.numUndeliveredMessages'` | Message count | Warn — undelivered messages will be lost |

**WARN**: Deleting a subscription is **IRREVERSIBLE**. All undelivered and in-flight messages are permanently lost.

**CLI**: `gcloud pubsub subscriptions delete "{{user.subscription_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --quiet`

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --quiet 2>&1 || echo "✅ Subscription confirmed deleted"`

### Publish Message

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic exists | `gcloud pubsub topics describe "{{user.topic_id}}" --quiet` | Exit 0 | HALT — create topic first |

**CLI**: `gcloud pubsub topics publish "{{user.topic_id}}" --message="{{user.message_data}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Variants*: `--attribute=key=value`, `--ordering-key="{{user.ordering_key}}"`

**Validate**: `jq '.messageIds[0]'` — non-empty message ID confirms publish.

### Pull Message

**Pre-flight**: Subscription exists.

**CLI (pull)**: `gcloud pubsub subscriptions pull "{{user.subscription_id}}" --auto-ack --limit={{user.max_messages:-10}} --format="json"`
*Extract*: `jq '.[0].ackId, .[0].message.data, .[0].message.messageId, .[0].message.publishTime, .[0].message.attributes'`

**CLI (no ack)**: `gcloud pubsub subscriptions pull "{{user.subscription_id}}" --limit={{user.max_messages:-10}} --format="json"`
*Manual ack*: `gcloud pubsub subscriptions ack "{{user.subscription_id}}" --ack-ids="{{output.ack_id}}"`

**Validate**: Non-empty result set or "no messages available" message.

### Configure Dead-Letter Topic (DLQ)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| DLQ topic exists | `gcloud pubsub topics describe "{{user.dead_letter_topic}}" --quiet` | Exit 0 | HALT — create DLQ topic first |
| Fetch project number | `gcloud projects describe "{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(projectNumber)"` | Numeric value | HALT — project not found |

**Pre-flight**: Grant Pub/Sub SA publisher role on DLQ topic:
```bash
PROJECT_NUMBER=$(gcloud projects describe "{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(projectNumber)")
gcloud pubsub topics add-iam-policy-binding "{{user.dead_letter_topic}}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher" --format="json"
```

**CLI**: `gcloud pubsub subscriptions update "{{user.subscription_id}}" --dead-letter-topic="{{user.dead_letter_topic}}" --max-delivery-attempts="{{user.max_delivery_attempts:-5}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '.deadLetterPolicy'` — confirm `deadLetterTopic` and `maxDeliveryAttempts`.

### Configure Retry Policy

**CLI (minimum backoff)**: `gcloud pubsub subscriptions update "{{user.subscription_id}}" --min-retry-delay="{{user.min_retry_delay:-10s}}" --max-retry-delay="{{user.max_retry_delay:-600s}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '.retryPolicy'`

### Create Snapshot

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Subscription exists | `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --quiet` | Exit 0 | HALT |
| Snapshot name unique | `gcloud pubsub snapshots describe "{{user.snapshot_id}}" --quiet` | NOT_FOUND | HALT — snapshot exists |

**CLI**: `gcloud pubsub snapshots create "{{user.snapshot_id}}" --subscription="{{user.subscription_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

**Validate**: `gcloud pubsub snapshots describe "{{user.snapshot_id}}" --format="json" | jq '{name, subscription, expireTime}'`

### Seek to Snapshot

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Snapshot exists | `gcloud pubsub snapshots describe "{{user.snapshot_id}}" --quiet` | Exit 0 | HALT — snapshot not found |
| Snapshot not expired | `gcloud pubsub snapshots describe "{{user.snapshot_id}}" --format="json" | jq -r '.expireTime'` | Future timestamp | HALT — snapshot expired (max 7 days) |

**CLI**: `gcloud pubsub subscriptions seek "{{user.subscription_id}}" --snapshot="{{user.snapshot_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions pull "{{user.subscription_id}}" --auto-ack --limit=1 --format="json"` — messages replayed from snapshot point.

### Seek to Timestamp

**CLI**: `gcloud pubsub subscriptions seek "{{user.subscription_id}}" --time="{{user.seek_timestamp}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

**Validate**: Pull messages and confirm timestamps are ≥ seek timestamp.

### Set Topic IAM

**CLI**:
- Add: `gcloud pubsub topics add-iam-policy-binding "{{user.topic_id}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`
- Remove: `gcloud pubsub topics remove-iam-policy-binding "{{user.topic_id}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`

**Validate**: `gcloud pubsub topics get-iam-policy "{{user.topic_id}}" --format="json" | jq '.bindings[] | select(.role == "{{user.role}}")'`

### Set Subscription IAM

**CLI**:
- Add: `gcloud pubsub subscriptions add-iam-policy-binding "{{user.subscription_id}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`
- Remove: `gcloud pubsub subscriptions remove-iam-policy-binding "{{user.subscription_id}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`

**Validate**: `gcloud pubsub subscriptions get-iam-policy "{{user.subscription_id}}" --format="json" | jq '.bindings[] | select(.role == "{{user.role}}")'`

### Backlog Diagnostics

**CLI**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '{numUndeliveredMessages, oldestUnackedMessageAge, messageRetentionDuration}'`

**Full diagnostic**: See [references/monitoring.md](references/monitoring.md) for Cloud Monitoring queries and alert policies.

**Alert on backlog**:
```bash
gcloud alpha monitoring policies create \
  --display-name="PubSub-Backlog-Alert" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" AND metric.labels.subscription_id="{{user.subscription_id}}"' \
  --condition-threshold-value=10000 \
  --condition-duration=300s
```

## Quality Gate (GCL)

| Property | Value |
|----------|-------|
| Classification | **required** (Delete subscription/topic + DLQ config) |
| max_iter | 2 |
| Most-scrutinized | Delete Subscription, Delete Topic, DLQ Configuration, Seek |

- **Rubric**: [references/rubric.md](references/rubric.md)
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency (P0 — 强制)

| Rule | Implementation |
|------|---------------|
| **TE-1** API query > static | Use `gcloud pubsub topics list --format="json"` instead of hardcoding |
| **TE-2** No docstrings | `#` comments only in SDK snippets |
| **TE-3** Compact errors | ≤3 columns, 1 row per code |
| **TE-4** Centralized JSON | See [references/api-sdk-usage.md](references/api-sdk-usage.md) |
| **TE-5** YAML anchors | See [assets/example-config.yaml](assets/example-config.yaml) |
| **TE-6** No duplication | SKILL.md = what; references/ = how |
| **TE-7** Advanced content | AIOps/FinOps in `references/advanced/` |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, at-least-once delivery, quotas, Prerequisites
- [API & SDK Usage](references/api-sdk-usage.md) — REST API map, Python/Go SDK code
- [gcloud Usage](references/gcloud-usage.md) — CLI commands for all operations
- [Troubleshooting](references/troubleshooting.md) — Error codes (≥10), diagnostics, recovery
- [Integration](references/integration.md) — Go bootstrap, env vars, credential rules
- [Monitoring](references/monitoring.md) — Metrics, dashboards, alerts
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Rubric](references/rubric.md) — GCL scoring
- [Prompt Templates](references/prompt-templates.md) — GCL templates

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **IAM**: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) — Service accounts and permissions
- **GCS**: [gcp-gcs-ops](../gcp-gcs-ops/SKILL.md) — Bucket notification topics
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate

## Operational Best Practices

- **Least privilege**: `roles/pubsub.publisher` (publish only), `roles/pubsub.subscriber` (pull only), `roles/pubsub.editor` (manage), `roles/pubsub.admin` (full)
- **Security**: Use push authentication (OIDC), VPC-SC, CMEK for sensitive messages
- **Reliability**: Always configure dead-letter topics with ≥5 max delivery attempts
- **Ordering**: Use ordering keys only when message order matters (adds latency)
- **Exactly-once**: Enable for critical workloads; adds deduplication overhead
- **Backlog**: Monitor `num_undelivered_messages` and `oldest_unacked_message_age`
- **Naming**: `{project}-{env}-{purpose}-{sequence}` — lowercase, hyphenated
