# Core Concepts — Cloud Storage

## Architecture

Google Cloud Storage (GCS) is a unified object storage service for any amount of data. Buckets are the fundamental containers, and objects are the data blobs stored within them.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Bucket** | Container for objects (globally unique name) | Global |
| **Object** | Immutable data blob with metadata and generation number | Within a bucket |
| **Storage Class** | Performance/availability/cost tier for objects | Per object or bucket default |
| **Generation** | Version number for each object write (monotonically increasing) | Per object |
| **Object Hold** | Event-based or temporary hold preventing deletion/replacement | Per object |
| **Lifecycle Rule** | Automated transition or deletion based on conditions | Per bucket |
| **Retention Policy** | Minimum duration objects must be kept before deletion | Per bucket |

### Locations

| Type | Examples | SLA |
|------|----------|-----|
| **Multi-region** | `US`, `EU`, `ASIA` | 99.95% (multi-region) |
| **Dual-region** | `NAM4`, `EUR4` | 99.95% (dual-region) |
| **Region** | `us-central1`, `europe-west1` | 99.90% (regional) |

### Storage Classes

| Class | Min Storage Duration | Retrieval Cost | Use Case |
|-------|---------------------|----------------|----------|
| **STANDARD** | None | None | Active, frequently accessed |
| **NEARLINE** | 30 days | Low | >30 day retention, accessed <1x/month |
| **COLDLINE** | 90 days | Moderate | >90 day retention, accessed <1x/quarter |
| **ARCHIVE** | 365 days | High | >365 day retention, archival/backup |

## Quotas

Check current buckets quota:
```bash
gcloud storage buckets list --format="json" | jq 'length'
```

GCS quotas per project:
| Resource | Default Limit |
|----------|---------------|
| Buckets per project | 100 (can request increase) |
| Object count per bucket | Unlimited |
| Object size per upload | 5 TiB max (single PUT = 5 GiB, composite via multipart) |
| Rate: Read (GET) | 10,000 object operations/second |
| Rate: Write (PUT) | 5,000 object operations/second |
| Rate: List (GET Bucket) | 5,000 bucket operations/second |

Check per-request rate limits with:
```bash
gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json"
```

## Dependencies

| Depend On | Reason |
|-----------|--------|
| IAM | Bucket and object permissions |
| Pub/Sub | Bucket notification to Pub/Sub topics |
| Cloud KMS | CMEK encryption key management |
| Cloud Monitoring | Storage metrics and alerts |
| VPC Service Controls | Data exfiltration prevention |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Bucket accidentally deleted | All objects lost | Enable versioning, set up Object Lifecycle rules, use retention policies |
| Multi-region unavailable (rare) | Access denied | Dual-region or another multi-region; multi-homing across providers |
| Quota exhausted | Can't create buckets | Request increase |
| Rate limit exceeded | Partial failures | Implement exponential backoff |
| Retention lock (if unintended) | Permanent data governance | Never lock unless 100% certain; consider Object holds first |

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per [enhanced-self-healing-framework.md](../../gcp-skill-generator/references/enhanced-self-healing-framework.md). Each step has >= 3 error-handling strategies.

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
           pip install --quiet --user google-cloud-storage
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
   gcloud storage buckets list --limit=1 --format="json" &>/dev/null && echo "✅ GCS API OK"
   gsutil ls &>/dev/null && echo "✅ gsutil OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.