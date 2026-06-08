# Monitoring & Alerts — Cloud Monitoring

## Cloud Monitoring Metrics About Itself

| Metric | Type | Description | Use Case |
|--------|------|-------------|----------|
| `monitoring.googleapis.com/monitoring/query/response_count` | counter | Number of time series query responses | Track query load |
| `monitoring.googleapis.com/monitoring/query/latencies` | distribution | Query latency distribution | Detect slow queries |
| `monitoring.googleapis.com/monitoring/alert_policies/count` | gauge | Number of alert policies | Monitor policy sprawl |
| `monitoring.googleapis.com/monitoring/notification_channels/count` | gauge | Number of notification channels | Audit channel coverage |
| `monitoring.googleapis.com/monitoring/uptime_checks/response_count` | counter | Uptime check response count | Track check execution |
| `monitoring.googleapis.com/monitoring/uptime_checks/response_latencies` | distribution | Uptime check latency | Detect endpoint degradation |

## Dashboard Layout Templates

### Infrastructure Overview

```json
{
  "displayName": "Infrastructure Overview",
  "gridLayout": {
    "columns": "2",
    "widgets": [
      {
        "title": "CPU Utilization",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"gce_instance\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\"",
                "aggregation": {
                  "alignmentPeriod": "300s",
                  "perSeriesAligner": "ALIGN_MEAN",
                  "crossSeriesReducer": "REDUCE_MEAN"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Memory Usage",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"gce_instance\" AND metric.type=\"agent.googleapis.com/memory/bytes_used\"",
                "aggregation": {
                  "alignmentPeriod": "300s",
                  "perSeriesAligner": "ALIGN_MEAN"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Disk IOPS",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"gce_instance\" AND metric.type=\"compute.googleapis.com/instance/disk/read_ops_count\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Network Throughput",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"gce_instance\" AND metric.type=\"compute.googleapis.com/instance/network/received_bytes_count\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      }
    ]
  }
}
```

## Alert Policy Templates

### Monitoring Health — Alert Policy Count

```json
{
  "displayName": "Monitoring: Excessive Alert Policies",
  "combiner": "OR",
  "conditions": [{
    "displayName": "Alert policy count > 100",
    "conditionThreshold": {
      "filter": "metric.type=\"monitoring.googleapis.com/monitoring/alert_policies/count\"",
      "aggregations": [{
        "alignmentPeriod": "300s",
        "perSeriesAligner": "ALIGN_MEAN",
        "crossSeriesReducer": "REDUCE_SUM"
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": 100,
      "duration": "300s"
    }
  }],
  "documentation": {
    "content": "Alert policy count exceeds 100. Review and consolidate unused policies.",
    "mimeType": "text/markdown"
  }
}
```

### Uptime Check Failure Rate

```json
{
  "displayName": "Monitoring: Uptime Check Failure Rate",
  "combiner": "OR",
  "conditions": [{
    "displayName": "Uptime check failures > 3 in 5 min",
    "conditionThreshold": {
      "filter": "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/monitoring/uptime_checks/response_count\"",
      "aggregations": [{
        "alignmentPeriod": "300s",
        "perSeriesAligner": "ALIGN_COUNT",
        "crossSeriesReducer": "REDUCE_COUNT_FALSE"
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": 3,
      "duration": "300s"
    }
  }]
}
```

## Log-Based Metrics

### Error Rate from Application Logs

```json
{
  "metricDescriptor": {
    "name": "projects/PROJECT/metricDescriptors/log_based_error_count",
    "type": "logging.googleapis.com/user/app_error_count",
    "metricKind": "DELTA",
    "valueType": "INT64",
    "description": "Count of ERROR-level application log entries"
  },
  "filter": "resource.type=\"gce_instance\" AND severity>=ERROR AND logName=~\"projects/.+/logs/application\"",
  "bucketOptions": {
    "linearBuckets": {
      "numFiniteBuckets": 10,
      "width": 1,
      "offset": 0
    }
  }
}
```

### Latency Distribution from Logs

```json
{
  "metricDescriptor": {
    "name": "projects/PROJECT/metricDescriptors/log_based_request_latency",
    "type": "logging.googleapis.com/user/request_latency",
    "metricKind": "DELTA",
    "valueType": "DISTRIBUTION",
    "description": "Request latency distribution extracted from logs"
  },
  "filter": "resource.type=\"gce_instance\" AND jsonPayload.eventType=\"request_complete\"",
  "labelExtractors": {
    "method": "EXTRACT(jsonPayload.method)",
    "status": "EXTRACT(jsonPayload.statusCode)"
  },
  "bucketOptions": {
    "exponentialBuckets": {
      "growthFactor": 2,
      "numFiniteBuckets": 20,
      "scale": 1.0
    }
  }
}
```

## Anomaly Patterns

| Pattern | Possible Cause | Recommended Action |
|---------|---------------|-------------------|
| Alert storm (many policies firing simultaneously) | Cascading failure or misconfigured thresholds | Use alert policy grouping; implement suppression windows |
| Metrics gaps (no data for N minutes) | Agent crash or network partition | Set up alert for missing metrics; configure dead-man's switch |
| Notification channel failures | Endpoint down or auth expired | Rotate to backup channel; verify webhook health |
| Custom metric descriptor churn | Application redeploying with changing schema | Standardize metric names in CI/CD; enforce naming convention |
| Dashboard load timeout | Too many widgets or overly broad queries | Limit to 50 widgets per dashboard; use pre-aggregated metrics |
