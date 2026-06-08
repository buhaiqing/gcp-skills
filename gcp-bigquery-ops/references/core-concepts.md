# Core Concepts — Cloud BigQuery

## Architecture

Google Cloud BigQuery is a fully-managed, serverless data warehouse that provides fast SQL queries over large datasets. It uses **storage/compute separation** with a columnar storage format (Capacitor) and Dremel query engine.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Dataset** | Container for tables, views, routines (regional or multi-regional) | Project-scoped |
| **Table** | Structured data in columnar format (Capacitor) | Within a dataset |
| **View** | Virtual table defined by a SQL query (standard SQL) | Within a dataset |
| **Materialized View** | Pre-computed result set, automatically refreshed | Within a dataset |
| **Routine** | User-defined function (SQL or JavaScript) | Within a dataset |
| **Partition** | Table split by date/timestamp/integer/ingestion time | Within a table |
| **Cluster** | Sorted storage within partitions for filter optimization | Within a table |
| **Job** | Unit of compute (QUERY, LOAD, EXTRACT, COPY) | Project-scoped |
| **Slot** | Virtual CPU unit for query execution (200 slots = 1 reserved unit) | Project-scoped |
| **Reservation** | Pre-purchased compute capacity (flat-rate pricing) | Project-scoped |

### Locations

| Type | Examples | Use Case |
|------|----------|----------|
| **Multi-region** | `US`, `EU` | Cross-region analytics, highest availability |
| **Region** | `us-central1`, `europe-west1` | Data residency, lower latency for regional compute |

### Storage Format

BigQuery uses **Capacitor**, a columnar storage format optimized for analytics:
- Column-oriented storage enables efficient predicate pushdown
- Automatic compression reduces storage costs
- Block-level metadata enables pruning of irrelevant data

## Partitioning

| Type | Field | Description |
|------|-------|-------------|
| **Time-unit** | DATE/TIMESTAMP/DATETIME column | Partition by day/hour/month/year |
| **Ingestion-time** | `_PARTITIONTIME`, `_PARTITIONDATE` | Auto-populated pseudo-columns |
| **Integer range** | INTEGER column | Partition by numeric range (start, end, interval) |

**Special pseudo-columns for ingestion-time partitioning**:
- `_PARTITIONTIME`: TIMESTAMP of ingestion
- `_PARTITIONDATE`: DATE of ingestion

**Partition Pruning**: Filter on partition column to reduce bytes processed (cost optimization).

```sql
-- Good: partition pruning applied
SELECT * FROM `project.dataset.table` WHERE date_column = '2026-06-08';

-- Bad: full table scan
SELECT * FROM `project.dataset.table`;
```

## Clustering

| Aspect | Details |
|--------|---------|
| Columns | Up to 4 columns |
| Data types | All types except ARRAY, STRUCT |
| Order | First column has highest impact |
| Benefit | Automatic block pruning for filter/aggregation queries |

Clustering works on top of partitioning — data is first partitioned, then sorted within each partition.

## Job Types

| Type | Purpose | Cost |
|------|---------|------|
| **QUERY** | Execute SQL query | $5/TB processed (on-demand) |
| **LOAD** | Import data from GCS/local | Free |
| **EXTRACT** | Export data to GCS | Free |
| **COPY** | Copy table within/across projects | Free |

## Pricing

| Model | Cost | Best For |
|-------|------|----------|
| **On-Demand** | $5/TB processed, first 1TB free/month | Variable workloads |
| **Flat-Rate** | $400/slot/month (flexible reservations) | Predictable, high-volume workloads |
| **Editions** | Enterprise/Enterprise Plus (2024+) | Advanced features, governance |

**Storage**: $0.02/GB/month (active), $0.01/GB/month (long-term, 90+ days no modification)

**Free tier**: 1TB on-demand query processing per month, 10GB storage per month

## Quotas

Check current quotas:
```bash
bq show --format=prettyjson "{{user.dataset_id}}" 2>&1 | grep -i quota
```

| Resource | Default Limit |
|----------|---------------|
| Datasets per project | 10,000 (can request increase) |
| Tables per dataset | Unlimited (practical limit ~1M) |
| Columns per table | 10,000 (nested/repeated counts toward limit) |
| Query size (API) | 1MB query string |
| Response size (API) | 1GB (15GB in UI) |
| Concurrent queries | 100 (on-demand), reservation-dependent (flat-rate) |
| Queries per day | 10,000 (can request increase) |
| Table size | 2TB per table row (100MB per row) |
| Load job file size | 5TB uncompressed |
| Export job file size | 1GB per file (use wildcard for large exports) |

Check per-request rate limits with:
```bash
bq ls --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=prettyjson | head -5
```

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Cloud Storage | Data import/export, external tables |
| IAM | Dataset and table permissions |
| Cloud KMS | CMEK encryption for data at rest |
| Cloud Monitoring | Slot utilization, query metrics, cost alerts |
| VPC Service Controls | Data exfiltration prevention |
| Cloud Logging | Audit logging for dataset/table access |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Dataset accidentally deleted | All tables lost | Use dataset access controls, backup critical tables |
| Table accidentally deleted | Data lost | Enable table snapshot, export to GCS backup |
| Slot exhaustion | Queries queued/pending | Use flat-rate reservations, optimize queries |
| Quota exhausted | Can't create resources | Request increase, clean up unused resources |
| Cost spike from expensive query | Billing shock | Use dry-run first, set billing alerts, partition pruning |
| Cross-region data transfer | Performance impact | Co-locate datasets with compute resources |

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per [enhanced-self-healing-framework.md](../../gcp-skill-generator/references/enhanced-self-healing-framework.md). Each step has >= 3 error-handling strategies.

1. **Install gcloud CLI** (includes `bq`):
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
           pip install --quiet --user google-cloud-bigquery
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
   bq ls --project_id="$CLOUDSDK_CORE_PROJECT" --max_results=1 &>/dev/null && echo "✅ BigQuery API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.
