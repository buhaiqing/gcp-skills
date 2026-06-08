# Troubleshooting — Cloud Monitoring

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Filter syntax error or bad request | Verify metric type, filter, JSON structure |
| PERMISSION_DENIED / 403 | Missing IAM role | Grant monitoring.viewer/editor/admin |
| NOT_FOUND / 404 | Resource ID not found | List to find correct ID |
| ALREADY_EXISTS / 409 | Duplicate name | Use unique name or update existing |
| QUOTA_EXCEEDED / 429 | Quota reached | Delete unused or request increase |
| INTERNAL / 500 | Server error | Retry with backoff |
| UNAVAILABLE / 503 | Service unavailable | Retry (5s, 10s, 20s backoff) |
| DEADLINE_EXCEEDED / 504 | Query timeout | Narrow time range or filter scope |
| FAILED_PRECONDITION / 400 | Precondition not met | Verify channel verification, resource state |
| ABORTED / 409 | Etag conflict (dashboards) | Re-fetch etag and retry |
| RESOURCE_EXHAUSTED / 429 | Rate limit exceeded | Reduce request rate |
| UNAUTHENTICATED / 401 | Token expired | Refresh access token |

## Diagnostic Order

1. Verify credentials: `gcloud auth print-access-token --quiet`
2. Verify project: `gcloud config get-value project`
3. Verify API enabled: `gcloud services list --enabled --filter="config:monitoring.googleapis.com"`
4. List resources: `gcloud monitoring {resource} list`
5. Check Cloud Logging for Monitoring API errors: `resource.type="api" AND protoPayload.serviceName="monitoring.googleapis.com"`

## Common Issues

### No Metrics Data

**Symptoms**: Time series query returns empty `[]`.

**Diagnostic steps**:
```bash
# 1. Verify metric descriptor exists
gcloud monitoring metrics list --filter="metric.type='YOUR_METRIC'" --project=PROJECT

# 2. Check monitored resource labels
gcloud monitoring metrics list --format=json | jq '.[].monitoredResourceTypes'

# 3. Verify time range (data may be delayed up to 5 min)
# Use interval.endTime = now, interval.startTime = now - 1h

# 4. Check metric ingestion for custom metrics
gcloud logging read 'resource.type="global" AND log_name="projects/PROJECT/logs/monitoring.googleapis.com%2Fmetric_descriptor"' --limit=10
```

**Resolution**:
- Confirm the source is publishing metrics (agent running, SDK writing)
- Verify metric labels match monitored resource requirements
- Wait up to 5 minutes for metric ingestion delay
- For custom metrics: check that the project has not exceeded the 1,000 metric descriptor limit

### Alert Not Firing

**Symptoms**: Metric exceeds threshold but no alert triggered.

**Diagnostic steps**:
```bash
# 1. Verify alert policy exists and is enabled
gcloud monitoring alert-policies list --filter="displayName='POLICY_NAME'" --format=json \
  | jq '.[] | {enabled, combiner, conditions: [.conditions[].displayName]}'

# 2. Verify condition filter matches actual metric
# Run the same filter as a time series query

# 3. Check notification channels
gcloud monitoring channels list --format=json | jq '.[] | {name, type, verificationStatus}'

# 4. Verify threshold and duration
gcloud monitoring alert-policies describe POLICY_ID --format=json \
  | jq '.conditions[] | .conditionThreshold | {thresholdValue, duration, comparison}'
```

**Resolution**:
- Confirm filter exactly matches the metric's resource type and labels
- Check that the condition duration (e.g., 300s) has elapsed
- Verify notification channel is VERIFIED (not UNVERIFIED)
- Check combiner: `AND` requires ALL conditions, `OR` requires ANY
- Verify the metric data has sufficient points for the aggregation period

### Notification Not Received

**Symptoms**: Alert fired but no notification delivered.

**Diagnostic steps**:
```bash
# 1. Check notification channel verification status
gcloud monitoring channels describe CHANNEL_ID --format=json | jq '.verificationStatus'

# 2. Verify channel labels are correct
gcloud monitoring channels describe CHANNEL_ID --format=json | jq '.labels'

# 3. Check if alert policy references the channel
gcloud monitoring alert-policies describe POLICY_ID --format=json | jq '.notificationChannels'
```

**Resolution**:
- **Email**: Check spam; verify `email_address` label is correct; resend verification
- **Slack**: Verify `auth_token` is valid and not expired; verify `channel_name` exists
- **Webhook**: Verify endpoint is reachable; check webhook server logs for POST requests
- **PagerDuty**: Verify `service_key` is correct and PagerDuty integration is active
- If channel status is `UNVERIFIED`, run `gcloud monitoring channels send-verification-code CHANNEL_ID`

### Dashboard Stale / Missing Widgets

**Symptoms**: Dashboard shows old data or widgets are blank.

**Diagnostic steps**:
```bash
# 1. Fetch current dashboard config
gcloud monitoring dashboards describe DASHBOARD_ID --format=json \
  | jq '.gridLayout.widgets[] | {title, dataSet: .xyChart.dataSets[].timeSeriesQuery.timeSeriesFilter.filter}'

# 2. Verify widget filters still match available metrics
# Compare each filter against gcloud monitoring metrics list

# 3. Check etag for concurrent modifications
gcloud monitoring dashboards describe DASHBOARD_ID --format=json | jq '.etag'
```

**Resolution**:
- If metric type was renamed/deleted, update widget filter
- If etag conflict, re-fetch and apply changes with latest etag
- For time-range issues, verify widget's time series query interval
- Recreate widgets that reference deleted metric descriptors

### Uptime Check False Positive

**Symptoms**: Uptime check reports failure but service is running.

**Diagnostic steps**:
```bash
# 1. Check uptime check config
gcloud monitoring uptime describe CONFIG_ID --format=json \
  | jq '{hostname, checkType, period, timeout, regions}'

# 2. Verify hostname resolves
nslookup hostname

# 3. Check from Monitoring check IPs (test manually)
gcloud monitoring uptime ips --format=json | jq '.[] | .ipAddress'

# 4. Check if firewall blocks Monitoring IPs
# Source: https://cloud.google.com/monitoring/uptime-checks/regions
```

**Resolution**:
- Increase `timeout` if service is slow (default 10s may be too short)
- Add more regions to reduce false positives from single-region issues
- Verify firewall allows inbound from Monitoring check IPs (0.0.0.0/0 for HTTP/HTTPS)
- For HTTPS checks, verify SSL certificate is valid and not expired
- Check `checkType`: HTTP vs HTTPS vs TCP must match the service

### Custom Metric Rejected

**Symptoms**: `INVALID_ARGUMENT` when creating or writing custom metrics.

**Diagnostic steps**:
```bash
# 1. Check if metric descriptor already exists
gcloud monitoring metrics list --filter="metric.type='custom.googleapis.com/YOUR_METRIC'" --project=PROJECT

# 2. Verify metric descriptor structure
# Check metric_kind (GAUGE/CUMULATIVE/DELTA) matches value_type

# 3. Check descriptor quota
gcloud monitoring metrics list --project=PROJECT --format=json | jq 'length'
```

**Resolution**:
- `metric_kind` must match: CUMULATIVE requires monotonically increasing values; GAUGE is point-in-time
- Labels in the write request must not exceed labels defined in the descriptor
- If 1,000 descriptor limit reached, delete unused descriptors before creating new ones
- Verify `metric.type` follows format: `custom.googleapis.com/{namespace}/{metric}` or `external.googleapis.com/{namespace}/{metric}`
