# Monitoring — Google Cloud Armor

## Key Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `securitypolicy.googleapis.com/request_count` | Total requests | — |
| `securitypolicy.googleapis.com/allowed_request_count` | Allowed requests | — |
| `securitypolicy.googleapis.com/denied_request_count` | Denied requests | > 0 (alert) |
| `securitypolicy.googleapis.com/throttled_request_count` | Throttled requests | > 0 (alert) |
| `securitypolicy.googleapis.com/total_traffic` | Total traffic volume | — |
| `securitypolicy.googleapis.com/adaptive_protection_score` | Adaptive protection score | < 50 (alert) |

## Cloud Monitoring Setup

### Dashboard Metrics

```yaml
# Security policy overview
- type: securitypolicy.googleapis.com/request_count
  view: FULL
- type: securitypolicy.googleapis.com/denied_request_count
  view: FULL
```

### Alert Policies

```yaml
# Alert on high denial rate
alertPolicy:
  displayName: "High Denial Rate"
  conditions:
    - displayName: "Denial rate > 10%"
      conditionThreshold:
        filter: "resource.type=\"security_policy\""
        comparison: COMPARISON_GT
        thresholdValue: 0.1
        duration: "300s"
```

## Logging

Enable security policy logging:

```bash
gcloud compute security-policies update {{user.policy_name}} \
  --enable-logging \
  --logging-metadata="include-all"
```

## Cost & Performance Metrics

| Metric | Description |
|--------|-------------|
| Request-based billing | Per-request charges |
| WAF rule evaluation | Minimal latency impact |
| Adaptive protection | ML model training cost |
