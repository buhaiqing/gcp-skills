# AIOps Anomaly Detection — Google Cloud Build

> Provides DevOps/SRE engineers with a guide to implementing AIOps-driven anomaly detection for Cloud Build — build failure pattern detection, build time anomalies, retry prediction, and automated remediation using Cloud Monitoring and log-based metrics.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Build Failure Pattern Detection](#build-failure-pattern-detection)
5. [Build Time Anomaly Detection](#build-time-anomaly-detection)
6. [Retry Prediction](#retry-prediction)
7. [Real-Time Alerting](#real-time-alerting)
8. [Automated Remediation](#automated-remediation)
9. [Log-Based Metrics](#log-based-metrics)
10. [Best Practices](#best-practices)
11. [See Also](#see-also)

## Overview

AIOps (Artificial Intelligence for IT Operations) uses machine learning and data analysis to detect anomalies in Cloud Build workloads. With Cloud Build's integration with Cloud Monitoring and Cloud Logging, you can:

- Detect build failure patterns (flaky tests, infrastructure issues, dependency failures)
- Identify build time anomalies (sudden slowdowns, cache misses)
- Predict retry probability (flag builds likely to fail before they run)
- Automate remediation responses (auto-retry, notification routing)

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Build failure spike | Rate change detection | High |
| Build time regression | Time-series anomaly | Medium |
| Flaky test detection | Pattern analysis | High |
| Cache miss spike | Metric threshold | Medium |
| Timeout increase | Trend analysis | Medium |
| Worker pool exhaustion | Capacity prediction | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Cloud Build Pipeline                             │
│                                                                          │
│  Build Requests                                                          │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐  │
│  │ Build Triggers │───►│ Cloud Build    │───►│ Cloud Logging       │  │
│  │ GitHub/Bitbucket│    │ Service        │    │ (Build Logs)        │  │
│  └────────────────┘    └────────────────┘    └──────────────────────┘  │
│                                                        │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌───────▼──────┐     ┌──────▼──────┐        │
│       │ Cloud       │      │ Log-Based    │     │ Alert       │        │
│       │ Monitoring  │      │ Metrics      │     │ Policy      │        │
│       │ (Metrics)   │      │              │     │             │        │
│       └─────────────┘      └──────────────┘     └─────────────┘        │
│                                   │                                     │
│                          ┌────────▼────────┐                           │
│                          │ Automated       │                           │
│                          │ Remediation     │                           │
│                          └─────────────────┘                           │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# 1. Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-build-project

# 3. Verify Cloud Build access
gcloud builds list --limit=1

# 4. Create notification channel (for alerts)
gcloud alpha monitoring channels create \
  --display-name="Cloud Build Alerts" \
  --type=email \
  --channel-labels=email_address=$ALERT_EMAIL
```

## Build Failure Pattern Detection

### Failure Rate Analysis

```bash
# Analyze build failure rate by day
gcloud logging read \
  'resource.type="build" "status":"FAILURE"' \
  --format='table[box](timestamp,resource.labels.build_id,textPayload)' \
  --order=desc \
  --limit=50

# Group failures by error type
gcloud logging read \
  'resource.type="build" "status":"FAILURE"' \
  --format='value(textPayload)' | \
  sort | uniq -c | sort -rn | head -20
```

### Common Failure Patterns

```bash
# 1. Docker build failures
gcloud logging read \
  'resource.type="build" "docker" AND "failed" AND "Step .*/RUN"' \
  --order=desc --limit=30

# 2. NPM/dependency failures
gcloud logging read \
  'resource.type="build" ("npm ERR" OR "yarn error" OR "package.json")' \
  --order=desc --limit=30

# 3. Permission/IAM failures
gcloud logging read \
  'resource.type="build" ("PERMISSION_DENIED" OR "IAM" OR "service account")' \
  --order=desc --limit=30

# 4. Network timeout failures
gcloud logging read \
  'resource.type="build" ("timeout" OR "connection refused" OR "ETIMEDOUT")' \
  --order=desc --limit=30
```

### Flaky Test Detection

```bash
# Detect flaky tests (tests that fail intermittently)
bq query --use_legacy_sql=false \
  "WITH build_results AS (
    SELECT
      build_id,
      TIMESTAMP_TRUNC(start_time, HOUR) as hour,
      CASE WHEN status = 'FAILURE' THEN 1 ELSE 0 END as failed
    FROM \`region-us\`.INFORMATION_SCHEMA.BUILD_STEPS
    WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  ),
  flaky_tests AS (
    SELECT
      build_id,
      SUM(failed) as failure_count,
      COUNT(*) as total_runs
    FROM build_results
    GROUP BY build_id
    HAVING failure_count > 0 AND failure_count < total_runs
  )
  SELECT
    build_id,
    failure_count,
    total_runs,
    ROUND(failure_count * 100.0 / total_runs, 2) as flake_rate
  FROM flaky_tests
  ORDER BY flake_rate DESC
  LIMIT 20"
```

## Build Time Anomaly Detection

### Build Time Distribution

```bash
# Get build time statistics
gcloud builds list \
  --filter='status=SUCCESS' \
  --format='table[box](id,createTime,duration,logUrl)' | head -20

# Calculate z-score for build duration
bq query --use_legacy_sql=false \
  "WITH build_times AS (
    SELECT
      build_id,
      TIMESTAMP_DIFF(end_time, start_time, SECOND) / 60 as duration_min
    FROM \`region-us\`.INFORMATION_SCHEMA.BUILD_STEPS
    WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  ),
  stats AS (
    SELECT
      AVG(duration_min) as mean_duration,
      STDDEV(duration_min) as stddev_duration
    FROM build_times
  )
  SELECT
    build_id,
    duration_min,
    ROUND((duration_min - mean_duration) / NULLIF(stddev_duration, 0), 2) as z_score
  FROM build_times
  CROSS JOIN stats
  WHERE ABS((duration_min - mean_duration) / NULLIF(stddev_duration, 0)) > 2
  ORDER BY z_score DESC"
```

### Cache Miss Detection

```bash
# Detect sudden cache miss rate increase
gcloud logging read \
  'resource.type="build" ("Using cache" OR "Cache miss" OR "Pulling cache")' \
  --order=desc --limit=100 | \
  grep -c "Cache miss"

# Monitor cache effectiveness
bq query --use_legacy_sql=false \
  \"WITH cache_stats AS (
    SELECT
      DATE(start_time) as day,
      COUNTIF(status = 'SUCCESS' AND log LIKE '%Using cache%') as cached_builds,
      COUNTIF(status = 'SUCCESS') as total_builds
    FROM \\\`region-us\\\`.INFORMATION_SCHEMA.BUILD_STEPS
    WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY day
  )
  SELECT
    day,
    cached_builds,
    total_builds,
    ROUND(cached_builds * 100.0 / total_builds, 2) as cache_hit_rate
  FROM cache_stats
  ORDER BY day DESC\"
```

### Build Time Trend Analysis

```bash
# Analyze build time trend
gcloud logging read \
  'resource.type="build" "duration" "seconds"' \
  --order=desc --limit=1000 | \
  jq -r '[select(.textPayload | contains("duration")) | .timestamp]' | \
  head -50
```

## Retry Prediction

### Failure Prediction Query

```bash
# Predict build failure based on historical patterns
bq query --use_legacy_sql=false \
  "WITH recent_builds AS (
    SELECT
      build_id,
      status,
      TIMESTAMP_DIFF(end_time, start_time, SECOND) / 60 as duration_min,
      ARRAY_LENGTH(steps) as step_count,
      start_time
    FROM \`region-us\`.INFORMATION_SCHEMA.BUILD_STEPS
    WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  ),
  patterns AS (
    SELECT
      CASE
        WHEN status = 'FAILURE' THEN 'FAILURE'
        WHEN duration_min > 30 THEN 'SLOW'
        WHEN step_count > 20 THEN 'COMPLEX'
        ELSE 'NORMAL'
      END as pattern_type,
      COUNT(*) as count
    FROM recent_builds
    GROUP BY 1
  )
  SELECT * FROM patterns ORDER BY count DESC"
```

### Retry Probability Scoring

```bash
# Score builds by retry probability
bq query --use_legacy_sql=false \
  "WITH build_features AS (
    SELECT
      build_id,
      status,
      TIMESTAMP_DIFF(end_time, start_time, SECOND) / 60 as duration_min,
      step_count,
      -- Feature: previous build failure
      LAG(status) OVER (ORDER BY start_time) = 'FAILURE' as prev_failed,
      -- Feature: cache miss
      log LIKE '%Cache miss%' as cache_miss
    FROM (
      SELECT
        build_id,
        status,
        start_time,
        end_time,
        ARRAY_LENGTH(steps) as step_count,
        log
      FROM \`region-us\`.INFORMATION_SCHEMA.BUILD_STEPS
    )
  )
  SELECT
    build_id,
    prev_failed,
    cache_miss,
    CASE
      WHEN prev_failed THEN 'HIGH'
      WHEN cache_miss THEN 'MEDIUM'
      ELSE 'LOW'
    END as retry_probability
  FROM build_features
  WHERE status = 'QUEUED'"
```

## Real-Time Alerting

### Build Failure Alert

```bash
# Create build failure alert policy
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/$CHANNEL_ID" \
  --display-name="Cloud Build Failure Alert" \
  --condition-display-name="Build Failure Rate > 10%" \
  --condition-filter='metric.type="cloudbuild.googleapis.com/builds/failure_count"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Build Time Regression Alert

```bash
# Create build time regression alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/$CHANNEL_ID" \
  --display-name="Build Time Regression" \
  --condition-display-name="Build Duration > 15 min" \
  --condition-filter='metric.type="cloudbuild.googleapis.com/builds/duration"' \
  --condition-threshold-value=900 \
  --condition-threshold-duration=600s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Worker Pool Exhaustion Alert

```bash
# Create worker pool capacity alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/$CHANNEL_ID" \
  --display-name="Worker Pool Exhaustion" \
  --condition-display-name="Worker Utilization > 90%" \
  --condition-filter='metric.type="cloudbuild.googleapis.com/worker_pools/utilization"' \
  --condition-threshold-value=0.9 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Retry Failed Builds

```bash
#!/bin/bash
# auto-retry-builds.sh

# Find failed builds in last hour
FAILED_BUILDS=$(gcloud builds list \
  --filter='status=FAILURE AND createTime>="$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)"' \
  --format='value(id)')

for BUILD_ID in $FAILED_BUILDS; do
  echo "Retrying build: $BUILD_ID"
  gcloud builds retry $BUILD_ID --quiet
done
```

### Auto-Scale Worker Pool

```bash
#!/bin/bash
# auto-scale-worker-pool.sh

POOL_NAME="my-worker-pool"
LOCATION="us-central1"
MAX_NODES=10
MIN_NODES=0

# Check current utilization
CURRENT_UTIL=$(gcloud builds worker-pools describe $POOL_NAME \
  --location=$LOCATION \
  --format=json | jq '.workerConfig.maxNodes')

# Get queue depth
QUEUE_DEPTH=$(gcloud builds list \
  --filter='status=QUEUED' \
  --limit=100 --format='value(id)' | wc -l)

# Scale based on queue
if [ $QUEUE_DEPTH -gt 20 ]; then
  NEW_NODES=$((MIN(MAX_NODES, QUEUE_DEPTH / 5)))
  echo "Scaling worker pool to $NEW_NODES nodes"
  gcloud builds worker-pools update $POOL_NAME \
    --location=$LOCATION \
    --worker-config=maxNodes=$NEW_NODES
fi
```

### Auto-Notify on Flaky Tests

```bash
#!/bin/bash
# notify-flaky-tests.sh

# Find flaky tests in last 24 hours
FLAKY_TESTS=$(bq query --use_legacy_sql=false \
  --format=json \
  "SELECT test_name, COUNT(*) as failure_count
   FROM build_tests
   WHERE status = 'FAILURE'
     AND start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
   GROUP BY test_name
   HAVING failure_count > 3" | jq -r '.[].test_name')

for TEST in $FLAKY_TESTS; do
  echo "Flaky test detected: $TEST - notifying team"
  # Send notification (e.g., to Slack, PagerDuty)
done
```

## Log-Based Metrics

### Create Custom Metrics

```bash
# Create log-based metric for build failures
gcloud logging metrics create build_failure_count \
  --description="Count of failed Cloud Builds" \
  --log-filter='resource.type="build" AND "FAILURE"'

# Create log-based metric for slow builds
gcloud logging metrics create slow_build_count \
  --description="Count of builds exceeding 15 minutes" \
  --log-filter='resource.type="build" AND "duration" AND "seconds":[900 TO *]'
```

### Build Step Duration Metrics

```bash
# Query build step durations
gcloud logging read \
  'resource.type="build" "Step .*: " duration' \
  --order=desc --limit=100 | \
  jq -r '.textPayload' | grep "Step.*duration" | \
  awk -F'duration:' '{print $2}' | sort -n
```

## Best Practices

1. **Enable Build Notifications**: Use Cloud Build notifications for Slack/Email
2. **Set Build Timeouts**: Prevent runaway builds with reasonable timeouts (default: 600s)
3. **Use Caching Aggressively**: Docker layer cache, dependency cache, artifact cache
4. **Monitor Build Metrics**: Track build success rate, duration, queue time trends
5. **Implement Retry Logic**: Auto-retry transient failures (network, quota)
6. **Use Failure Annotations**: Add failure reason to builds for pattern analysis
7. **Alert on Trends**: Not just thresholds — alert on rate-of-change

## See Also

- [Cloud Build Execution](../execution-flows.md)
- [Cloud Build Troubleshooting](../troubleshooting.md)
- [Cloud Build Monitoring](../monitoring.md)
- [Cloud Monitoring Metrics](https://cloud.google.com/monitoring/api/metrics)
- [Cloud Logging Log-Based Metrics](https://cloud.google.com/logging/docs/logs-based-metrics)
