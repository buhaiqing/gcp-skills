# Monitoring — Cloud Secret Manager

## Cloud Monitoring Metrics

### Available Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `secretmanager.googleapis.com/secret_version_bytes` | Gauge | bytes | Storage used by secret versions |
| `secretmanager.googleapis.com/active_secret_count` | Gauge | count | Number of active secrets |
| `secretmanager.googleapis.com/active_secret_version_count` | Gauge | count | Number of enabled secret versions |
| `secretmanager.googleapis.com/access_request_count` | Counter | count | Number of access requests |
| `secretmanager.googleapis.com/api_request_count` | Counter | count | Total API requests |
| `secretmanager.googleapis.com/api_request_latencies` | Distribution | ms | API request latency |
| `secretmanager.googleapis.com/rotation_request_count` | Counter | count | Number of rotation operations |

### Key Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High access latency | p99 > 500ms for 5min | Warning |
| Access request spike | > 80% of quota | Warning |
| Secret version storage high | > 90% of budget | Warning |
| Failed access requests | > 5 failures in 5min | Critical |

## Cloud Logging

### Audit Log Entries

| Operation | Log Name | Method |
|-----------|----------|--------|
| Create Secret | cloudaudit.googleapis.com/activity | google.cloud.secretmanager.v1.SecretManagerService.CreateSecret |
| Access Version | cloudaudit.googleapis.com/data_access | google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion |
| Delete Secret | cloudaudit.googleapis.com/activity | google.cloud.secretmanager.v1.SecretManagerService.DeleteSecret |
| Update Secret | cloudaudit.googleapis.com/activity | google.cloud.secretmanager.v1.SecretManagerService.UpdateSecret |
| IAM Policy Change | cloudaudit.googleapis.com/activity | google.cloud.secretmanager.v1.SecretManagerService.SetIamPolicy |

### Log-Based Metrics

```json
{
  "filter": "resource.type=\"secret_manager_secret\" AND protoPayload.methodName=\"AccessSecretVersion\"",
  "metric": {
    "name": "secret_access_count",
    "type": "COUNTER"
  }
}
```

## Dashboard Panels

### Recommended Panels

| Panel | Metric | Aggregation |
|-------|--------|-------------|
| Secret Access Rate | access_request_count | Rate (1m) |
| API Latency | api_request_latencies | p50, p95, p99 |
| Active Secrets | active_secret_count | Max |
| Storage Usage | secret_version_bytes | Sum |
| Error Rate | api_request_count (filter: status>=400) | Rate (1m) |

## Pub/Sub Notifications

### Rotation Events

When rotation is configured, Secret Manager publishes to the configured topic:
```json
{
  "eventType": "SECRET_VERSION_ROTATED",
  "secret": "projects/PROJECT/secrets/SECRET",
  "version": "VERSION_ID",
  "createTime": "2026-06-07T10:00:00Z"
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `SECRET_VERSION_ROTATED` | New version created via rotation |
| `SECRET_VERSION_ADDED` | Manual version addition |
