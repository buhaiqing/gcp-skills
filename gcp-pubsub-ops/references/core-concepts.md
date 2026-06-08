# Core Concepts — Cloud Pub/Sub

## Architecture

Google Cloud Pub/Sub is a fully-managed real-time messaging service that enables independent applications to exchange messages. Publishers send messages to **topics**, and subscribers receive messages from **subscriptions** attached to those topics.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Topic** | Named resource to which publishers send messages | Per project |
| **Subscription** | Named resource representing a message stream from a single topic to a subscriber | Per project |
| **Message** | Data payload (up to 1 MiB) with optional attributes and ordering key | Within a topic |
| **Dead-Letter Topic** | Topic where undeliverable messages are routed after max delivery attempts | Per project |
| **Snapshot** | Point-in-time capture of a subscription's backlog (retained up to 7 days) | Per project |
| **Schema** | Message format definition (Protobuf or Avro) for validation | Per project |

### Delivery Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Pull** | Subscriber actively requests messages via API/CLI | Batch processing, controlled throughput |
| **Push** | Pub/Sub delivers messages to a configured HTTPS endpoint | Real-time webhooks, event-driven services |
| **Streaming Pull** | Bi-directional streaming for high-throughput continuous pull | Low-latency stream processing |

### Delivery Semantics

| Semantic | Guarantee | Notes |
|----------|-----------|-------|
| **At-least-once** | Default — every message delivered ≥1 time | May have duplicates; idempotent consumers required |
| **Exactly-once** | Beta — deduplicated delivery | Enable via `--enable-exactly-once-delivery`; adds overhead |
| **Ordered** | Messages with same ordering key delivered in order | Enable via `--enable-message-ordering`; reduces throughput |

### Regions

| Type | Description |
|------|-------------|
| **Global** | Default — Pub/Sub is a global service with automatic regional replication |
| **Regional** | Messages stored in a specific region for data residency |

## Quotas

Check current topics/subscriptions:
```bash
gcloud pubsub topics list --format="json" | jq 'length'
gcloud pubsub subscriptions list --format="json" | jq 'length'
```

Pub/Sub quotas per project (default, query for current limits):
| Resource | Default Limit |
|----------|---------------|
| Topics per project | 10,000 (can request increase) |
| Subscriptions per topic | 10,000 |
| Messages per topic | 10,000 msg/sec (can request increase) |
| Message size | 1 MiB (including attributes) |
| Message retention | 7 days max |
| Snapshots per subscription | 10 (retained up to 7 days) |

## Dependencies

| Depend On | Reason |
|-----------|--------|
| IAM | Topic/subscription permissions, push auth |
| Cloud KMS | CMEK encryption for message data |
| Cloud Monitoring | Backlog metrics, alerting |
| Cloud Logging | Audit logs, message tracing |
| VPC Service Controls | Data exfiltration prevention |
| Cloud Run / Cloud Functions | Push endpoint targets |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Subscription deleted | All undelivered messages lost permanently | Configure DLQ before delete; snapshot before maintenance |
| DLQ overflow | Undeliverable messages lost after DLQ backlog full | Monitor DLQ backlog; set up alerts |
| Ordering violation | Messages with same key delivered out of order | Retry with same ordering key; disable ordering if not critical |
| Push endpoint down | Messages accumulate in backlog | Set retry policy; configure DLQ; use exponential backoff |
| Snapshot expired | Cannot replay to that point | Snapshots auto-expire in 7 days; recreate before maintenance |
| Ack deadline too short | Messages redelivered prematurely | Increase ack deadline; use streaming pull with modack |

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery. Each step has ≥3 error-handling strategies.

1. **Install gcloud CLI** (primary execution path):
   ```bash
   if ! command -v gcloud &> /dev/null; then
       curl https://sdk.cloud.google.com | bash 2>/dev/null \
       || (echo "⚠️ Installer failed, trying apt..." \
           && sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
       || (echo "⚠️ apt failed, trying manual..." \
           && wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
           && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
       exec -l $SHELL
       gcloud init
   fi
   ```

2. **Bootstrap Go runtime** (for JIT SDK fallback):
   ```bash
   if ! command -v go &> /dev/null; then
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
       || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       if [ -f /tmp/go-runtime/go/bin/go ]; then
           export PATH="/tmp/go-runtime/go/bin:$PATH"
       else
           echo "Go download failed. Using Python SDK as fallback."
           pip install --quiet --user google-cloud-pubsub
       fi
   fi
   ```

3. **Configure Credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
   || gcloud auth login --quiet
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

4. **Verify Configuration**:
   ```bash
   gcloud config list
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
   gcloud pubsub topics list --limit=1 --format="json" &>/dev/null && echo "✅ Pub/Sub API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.
