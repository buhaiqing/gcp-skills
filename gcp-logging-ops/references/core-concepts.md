# Core Concepts — Cloud Logging

## Architecture

Google Cloud Logging provides real-time log management and analysis. Logs are stored in **log buckets**, organized through **log views**, exported via **log sinks**, aggregated into **log-based metrics**, and filtered by **log exclusions**.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Log Bucket** | Storage container for log entries with configurable retention (1-3650 days) | Location (global or region) |
| **Log View** | Filtered subset of logs within a bucket for granular access control | Bucket |
| **Log Sink** | Routing rule that exports matching log entries to BigQuery, Pub/Sub, or Cloud Storage | Project |
| **Log-Based Metric** | Counter or distribution metric derived from log entry filter matches | Project |
| **Log Exclusion** | Filter that prevents matching log entries from being ingested or stored | Project |
| **_Required Bucket** | Protected system bucket for audit logs (400-day retention, cannot be deleted) | Location |
| **_Default Bucket** | Default bucket for all project logs (30-day retention) | Location |

### Log Entry Structure

Each log entry contains:
- `logName` — Full resource name of the log
- `resource` — Monitored resource that produced the log
- `timestamp` — Time the entry was written (RFC 3339)
- `severity` — DEFAULT / DEBUG / INFO / NOTICE / WARNING / ERROR / CRITICAL / ALERT / EMERGENCY
- `textPayload` / `jsonPayload` / `protoPayload` — Log content

## Quotas

Check current quotas:
```bash
gcloud logging quotas list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

Key limits:
| Resource | Default Limit |
|----------|--------------|
| Log buckets per location | 50 |
| Log sinks per project | 100 |
| Log metrics per project | 100 |
| Log exclusions per project | 100 |
| Log views per bucket | 10 |
| Log entries per API request | 1,000 |

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Cloud Monitoring | Log-based metrics integration |
| BigQuery | Log export destination (sinks) |
| Cloud Storage | Log export destination (sinks) |
| Pub/Sub | Log export destination (sinks) |
| Cloud KMS | CMEK encryption for log buckets |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| _Default bucket deleted | Logs stopped | Restore within 30d or use `_Required` |
| Sink misconfigured | Export interruption | Monitor sink delivery errors |
| Quota exhausted | Can't create buckets/sinks | Request increase |
| CMEK key revoked | Bucket becomes inaccessible | Restore key access |