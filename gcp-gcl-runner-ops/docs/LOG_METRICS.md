# GCL Log-Based Metrics

Cloud Logging log-based metrics for monitoring GCL (Generator-Critic-Loop) execution quality and performance.

## Overview

These metrics are derived from structured logs emitted by the GCL Runner. They enable:
- Real-time error rate monitoring
- Execution latency tracking
- Safety score visualization
- Autonomy ratio measurement

## Prerequisites

```bash
pip install google-cloud-logging pyyaml
gcloud auth application-default login
```

## Creating Metrics

### Option 1: Using Default Metrics

```bash
python3 scripts/create_log_metrics.py --project YOUR_PROJECT_ID
```

### Option 2: Using Custom Config

```bash
python3 scripts/create_log_metrics.py \
    --project YOUR_PROJECT_ID \
    --config log_metrics_config.yaml
```

### Option 3: Dry Run (Preview)

```bash
python3 scripts/create_log_metrics.py \
    --project YOUR_PROJECT_ID \
    --dry-run
```

## Available Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `gcl_error_rate` | DELTA_INT64 | Rate of GCL errors (ERROR logs per minute) |
| `gcl_warning_rate` | DELTA_INT64 | Rate of GCL warnings per minute |
| `gcl_execution_latency` | DELTA_DISTRIBUTION | Execution latency histogram |
| `gcl_safety_failures` | DELTA_INT64 | Count of safety=0 events |
| `gcl_autonomy_ratio` | GAUGE_FLOAT64 | Average autonomy ratio (0.0-1.0) |
| `gcl_max_iter_terminations` | DELTA_INT64 | Runs hitting max iterations |
| `gcl_generator_errors` | DELTA_INT64 | Generator agent errors |
| `gcl_critic_errors` | DELTA_INT64 | Critic agent errors |

## Using Metrics in Monitoring Dashboard

### 1. Create a Dashboard

```bash
gcloud monitoring dashboards create --config-from-file=/dev/stdin << 'EOF'
{
  "display_name": "GCL Observability",
  "mosaic_layout": {
    "columns": 2,
    "tiles": [
      {
        "width": 1,
        "height": 1,
        "widget": {
          "title": "GCL Error Rate",
          "xy_chart": {
            "data_sets": [{
              "time_series_query": {
                "time_series_filter": {
                  "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
                  "aggregation": {
                    "alignment_period": "60s",
                    "per_series_aligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

### 2. List Metrics

```bash
gcloud logging metrics list --project YOUR_PROJECT_ID
```

### 3. Describe a Metric

```bash
gcloud logging metrics describe gcl_error_rate --project YOUR_PROJECT_ID
```

## Example Alerting Policies

### Alert: High Error Rate

```bash
gcloud alpha monitoring policies create --notification-channels=CHANNEL_ID << 'EOF'
{
  "display_name": "GCL High Error Rate",
  "conditions": [{
    "display_name": "Error rate > 10/min",
    "condition_threshold": {
      "filter": 'metric.type="logging.googleapis.com/gcl_error_rate"',
      "comparison": "COMPARISON_GT",
      "threshold_value": 10,
      "duration": "60s",
      "aggregation": {
        "alignment_period": "60s",
        "per_series_aligner": "ALIGN_RATE"
      }
    }
  }]
}
EOF
```

### Alert: Safety Failure

```bash
gcloud alpha monitoring policies create --notification-channels=CHANNEL_ID << 'EOF'
{
  "display_name": "GCL Safety Failure",
  "conditions": [{
    "display_name": "Safety failures > 0",
    "condition_threshold": {
      "filter": 'metric.type="logging.googleapis.com/gcl_safety_failures"',
      "comparison": "COMPARISON_GT",
      "threshold_value": 0,
      "duration": "60s",
      "aggregation": {
        "alignment_period": "60s",
        "per_series_aligner": "ALIGN_SUM"
      }
    }
  }]
}
EOF
```

### Alert: High Latency

```bash
gcloud alpha monitoring policies create --notification-channels=CHANNEL_ID << 'EOF'
{
  "display_name": "GCL High Latency",
  "conditions": [{
    "display_name": "p95 latency > 5min",
    "condition_threshold": {
      "filter": 'metric.type="logging.googleapis.com/gcl_execution_latency"',
      "comparison": "COMPARISON_GT",
      "threshold_value": 300000,
      "duration": "300s",
      "aggregation": {
        "alignment_period": "60s",
        "per_series_aligner": "ALIGN_PERCENTILE_95"
      }
    }
  }]
}
EOF
```

### Alert: Low Autonomy

```bash
gcloud alpha monitoring policies create --notification-channels=CHANNEL_ID << 'EOF'
{
  "display_name": "GCL Low Autonomy",
  "conditions": [{
    "display_name": "Autonomy ratio < 0.5",
    "condition_threshold": {
      "filter": 'metric.type="logging.googleapis.com/gcl_autonomy_ratio"',
      "comparison": "COMPARISON_LT",
      "threshold_value": 0.5,
      "duration": "300s",
      "aggregation": {
        "alignment_period": "60s",
        "per_series_aligner": "ALIGN_MEAN"
      }
    }
  }]
}
EOF
```

## Log Filter Reference

| Metric | Cloud Logging Filter |
|--------|---------------------|
| Error rate | `severity=ERROR AND logger="gcl-runner"` |
| Warning rate | `severity=WARNING AND logger="gcl-runner"` |
| Safety failures | `severity=ERROR AND "SAFETY_FAIL" IN elements(message)` |
| Generator errors | `severity=ERROR AND "generator" IN elements(message)` |
| Critic errors | `severity=ERROR AND "critic" IN elements(message)` |

## Metric Types Explained

| Type | Description |
|------|-------------|
| `DELTA_INT64` | Count of events in the current interval |
| `GAUGE_FLOAT64` | Current value (averaged over interval) |
| `DELTA_DISTRIBUTION` | Histogram of values (for latency) |

## Verification

### Verify Metrics Exist

```bash
gcloud logging metrics list --project YOUR_PROJECT_ID | grep gcl_
```

### View Metric Details

```bash
gcloud logging metrics describe gcl_error_rate --format=json
```

### Query Logs Directly

```bash
gcloud logging read 'logger="gcl-runner"' --limit=10
```

## Troubleshooting

### Metrics Not Appearing

1. Verify GCL Runner is emitting logs with correct logger name
2. Check log sink is routing to Cloud Logging
3. Ensure project ID matches between script and logs

### Permission Denied

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
    --role="roles/logging.metricWriter"
```
