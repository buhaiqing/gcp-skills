# FinOps Cost Optimization — Google Cloud Build

> Provides DevOps/SRE engineers with a guide to optimizing Cloud Build costs — build minute pricing, caching strategies, parallel execution, and reserved capacity.

## Table of Contents

1. [Overview](#overview)
2. [Build Minute Cost Model](#build-minute-cost-model)
3. [Caching Strategies](#caching-strategies)
4. [Parallel Execution Optimization](#parallel-execution-optimization)
5. [Reserved Capacity Pricing](#reserved-capacity-pricing)
6. [Cost Monitoring](#cost-monitoring)
7. [Cost Optimization Commands](#cost-optimization-commands)
8. [Troubleshooting High Costs](#troubleshooting-high-costs)
9. [See Also](#see-also)

## Overview

Cloud Build costs primarily come from:

- **Build Minutes** — metered per build, per second after free tier
- **Machine Type** — larger workers cost more per minute
- **Network Egress** — data transfer out during builds
- **Artifact Storage** — Artifact Registry storage for build artifacts
- **Private Worker Pool** — dedicated infrastructure costs

Optimizing these can reduce Cloud Build spend by 30-60% for typical CI/CD workloads.

### Cost Drivers

| Resource | Pricing Model | Free Tier | Optimization Potential |
|----------|-------------|-----------|------------------------|
| Standard machine | $0.003/minute/core | 120 min/day | 30-50% |
| High-memory machine | $0.005/minute/core | — | 20-40% |
| Large machine | $0.010/minute/core | — | 20-30% |
| Private pool (e2-standard-4) | $0.026/hour + network | — | 15-25% |
| Build artifact storage | $0.10/GB/month | 0.5 GB | 40-60% |

## Build Minute Cost Model

### Pricing Breakdown

| Machine Type | CPU | Cost/minute | Cost/hour |
|-------------|-----|-------------|-----------|
| Standard (n1-standard-1) | 1 | $0.003 | $0.18 |
| High-memory (highmem) | 1 | $0.005 | $0.30 |
| Large (n1-standard-8) | 8 | $0.024 | $1.44 |
| Extra-large (n1-standard-32) | 32 | $0.096 | $5.76 |

### Cost Calculator

```bash
# Estimate build cost
ESTIMATE_MINUTES=300  # 5 hours
MACHINE_TYPE="n1-standard-2"  # 2 cores

case $MACHINE_TYPE in
  n1-standard-1) CORES=1; COST_PER_MIN=0.003 ;;
  n1-standard-2) CORES=2; COST_PER_MIN=0.006 ;;
  n1-standard-8) CORES=8; COST_PER_MIN=0.024 ;;
  n1-standard-32) CORES=32; COST_PER_MIN=0.096 ;;
esac

ESTIMATE_COST=$(echo "scale=4; $ESTIMATE_MINUTES * $COST_PER_MIN" | bc)
echo "Estimated build cost: \$$ESTIMATE_COST"
```

## Caching Strategies

### Docker Layer Caching

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/image:$COMMIT_SHA'
      - '-f'
      - 'Dockerfile'
      - '--cache-from'
      - 'gcr.io/$PROJECT_ID/image:latest'
      - '.'
    env:
      - 'BUILDKIT_INLINE_CACHE=1'
options:
  machineType: 'N1_HIGHCPU_8'
  logging: 'GCS_ONLY'
```

### GCS Cache for Non-Docker Builds

```bash
# Pre-pull cache from GCS
- name: 'gcr.io/cloud-builders/gsutil'
  args: ['cp', 'gs://$CACHE_BUCKET/cache.tar.gz', '/cache.tar.gz']

- name: 'ubuntu'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [ -f /cache.tar.gz ]; then
        tar -xzf /cache.tar.gz -C /
      fi
      # ... build steps ...

# Save cache to GCS
- name: 'gcr.io/cloud-builders/gsutil'
  args: ['cp', '/cache.tar.gz', 'gs://$CACHE_BUCKET/cache.tar.gz']
```

### BuildKit Cache Backend

```bash
# Use BuildKit with GCS cache backend
export DOCKER_BUILDKIT=1
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_CACHE_BUCKET=gs://my-cache-bucket
```

## Parallel Execution Optimization

### Dependency-Aware Step Scheduling

```yaml
# cloudbuild.yaml — parallel steps
steps:
  # These run in parallel
  - id: 'lint'
    name: 'gcr.io/cloud-builders/npm'
    entrypoint: 'npm'
    args: ['run', 'lint']

  - id: 'unit-tests'
    name: 'gcr.io/cloud-builders/npm'
    entrypoint: 'npm'
    args: ['test', '--', '--coverage']

  - id: 'security-scan'
    name: 'aquasec/trivy:latest'
    args: ['--format', 'table', '.']

  # This waits for lint + tests
  - id: 'build'
    name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/image:$COMMIT_SHA', '.']
    waitFor: ['lint', 'unit-tests']

  # This runs after build
  - id: 'push'
    name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/image:$COMMIT_SHA']
    waitFor: ['build']
```

### Concurrent Build Matrix

```bash
# Trigger parallel builds for different configurations
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_NODE_VERSION=18,_ENV=staging

gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_NODE_VERSION=20,_ENV=production
```

### Kaniko Cache for Fast Builds

```yaml
steps:
  - name: 'gcr.io/kaniko-project/executor:latest'
    args:
      - '--destination=gcr.io/$PROJECT_ID/image:$COMMIT_SHA'
      - '--cache=true'
      - '--cache-ttl=24h'
      - '--snapshotMode=redo'
```

## Reserved Capacity Pricing

### Calculate Reserved Capacity Needs

```bash
# Analyze build patterns
gcloud builds list \
  --filter='createTime>="2024-01-01T00:00:00Z"' \
  --format='table[box,title="Build History"](id,createTime,duration,status)' \
  --limit=100 | head -20

# Get average build duration
bq query --use_legacy_sql=false \
  "SELECT
    AVG(TIMESTAMP_DIFF(end_time, start_time, SECOND)) / 60 as avg_duration_min
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
```

### Private Worker Pool Cost Analysis

| Pool Config | Hourly Cost | Best For |
|------------|-------------|----------|
| e2-standard-4 | $0.026 + network | Small teams, <10 builds/day |
| e2-standard-8 | $0.052 + network | Medium teams, 10-50 builds/day |
| e2-highmem-8 | $0.065 + network | Memory-intensive builds |
| e2-standard-32 | $0.208 + network | Large monorepos, 50+ builds/day |

### Right-Size Worker Pools

```bash
# List worker pools
gcloud builds worker-pools list \
  --format='table[box](name,location,workerConfig.machineType,workerConfig.network)'

# Describe specific pool
gcloud builds worker-pools describe my-pool \
  --location=us-central1 \
  --format=json | jq '{machineType, minNodes, maxNodes}'
```

## Cost Monitoring

### Build Cost per Project

```bash
# Get build minute usage
gcloud monitoring metrics list \
  --filter='metric.type:cloudbuild.googleapis.com/builds' | head -10

# Create budget alert for Cloud Build
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="Cloud Build Monthly Budget" \
  --budget-amount=500 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --filter-credit-types-handled=true \
  --services=cloudbuild.googleapis.com
```

### Build Minute Utilization Dashboard

```bash
# Export build metrics to BigQuery
bq query --use_legacy_sql=false \
  "SELECT
    DATE(start_time) as build_date,
    COUNT(*) as build_count,
    SUM(duration_sec) / 60 as total_build_minutes,
    AVG(duration_sec) / 60 as avg_build_minutes
  FROM (
    SELECT
      start_time,
      end_time,
      TIMESTAMP_DIFF(end_time, start_time, SECOND) as duration_sec
    FROM UNNEST([
      SELECT TIMESTAMP('2024-01-01') as start_time, TIMESTAMP('2024-01-02') as end_time
    ])
  )
  GROUP BY build_date
  ORDER BY build_date DESC"
```

## Cost Optimization Commands

### Identify Expensive Builds

```bash
# Find longest running builds
gcloud builds list \
  --filter='status=SUCCESS' \
  --sort-by=~createTime \
  --limit=20 \
  --format='table[box](id,createTime,duration,status,logUrl)'

# Analyze build step timing
gcloud builds describe $BUILD_ID \
  --format=json | jq '.steps[] | {name, timing: .timing}'
```

### Clean Up Old Artifacts

```bash
# List artifact repositories
gcloud artifacts repositories list \
  --format='table[box](name,location,format)'

# Delete old images (keep last 10)
for repo in $(gcloud artifacts repositories list --format=value(name)); do
  gcloud container images list-tags $repo \
    --sort-by=timestamp \
    --limit=10 --format='get(digest)' | tail -n +11 | \
    while read digest; do
      gcloud container images delete "$repo@$digest" --quiet
    done
done
```

### Auto-Delete Builds History

```bash
# Delete builds older than 30 days
gcloud builds list \
  --filter='createTime<"2024-01-01T00:00:00Z"' \
  --format='value(id)' | \
  while read build_id; do
    gcloud builds delete $build_id --quiet
  done
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High build minute cost | No caching, large machine type | Enable Docker layer cache, use smaller machines |
| Unexpected private pool charges | Idle nodes running | Set minNodes=0, use scale-to-zero |
| Artifact storage bloat | No cleanup policy | Implement lifecycle policy on Artifact Registry |
| Concurrent build overspend | Unbounded parallelism | Set max concurrent builds in trigger settings |
| Network egress charges | Cross-region artifact pulls | Use regional Artifact Registry |

### Cost Investigation

```bash
# Get build minute consumption over time
gcloud projects get-ancestors $CLOUDSDK_CORE_PROJECT

# Check for slow builds consuming excess minutes
gcloud builds list \
  --filter='status=SUCCESS' \
  --format='table[box](id,createTime,duration,stepsCount)' | head -20

# Analyze step-level timing
gcloud builds describe $BUILD_ID \
  --format=json | jq '.steps[] | select(.timing.endTime) | {name, duration: (.timing.endTime - .timing.startTime)}'
```

## See Also

- [Cloud Build Execution](../execution-flows.md)
- [Cloud Build Troubleshooting](../troubleshooting.md)
- [Cloud Build Monitoring](../monitoring.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
