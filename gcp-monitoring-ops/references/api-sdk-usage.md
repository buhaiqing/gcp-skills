# API & SDK — Cloud Monitoring

## REST API

- Discovery doc: https://monitoring.googleapis.com/$discovery/rest?version=v3
- Base URL: https://monitoring.googleapis.com/v3/
- Auth: `Bearer $(gcloud auth print-access-token)`

## Operations Map

### Time Series & Metric Descriptors

| Goal | REST Method | Python SDK | Go SDK |
|------|------------|-----------|--------|
| List time series | GET /v3/{name}/timeSeries | MetricServiceClient.list_time_series() | MetricClient.ListTimeSeries() |
| List metric descriptors | GET /v3/{name}/metricDescriptors | MetricServiceClient.list_metric_descriptors() | MetricClient.ListMetricDescriptors() |
| Get metric descriptor | GET /v3/{name}/metricDescriptors/{id} | MetricServiceClient.get_metric_descriptor() | MetricClient.GetMetricDescriptor() |
| Create metric descriptor | POST /v3/{name}/metricDescriptors | MetricServiceClient.create_metric_descriptor() | MetricClient.CreateMetricDescriptor() |
| Delete metric descriptor | DELETE /v3/{name}/metricDescriptors/{id} | MetricServiceClient.delete_metric_descriptor() | MetricClient.DeleteMetricDescriptor() |

### Alert Policies

| Goal | REST Method | Python SDK | Go SDK |
|------|------------|-----------|--------|
| List alert policies | GET /v3/{name}/alertPolicies | AlertPolicyServiceClient.list_alert_policies() | AlertPolicyClient.ListAlertPolicies() |
| Get alert policy | GET /v3/{name} | AlertPolicyServiceClient.get_alert_policy() | AlertPolicyClient.GetAlertPolicy() |
| Create alert policy | POST /v3/{name}/alertPolicies | AlertPolicyServiceClient.create_alert_policy() | AlertPolicyClient.CreateAlertPolicy() |
| Update alert policy | PATCH /v3/{name} | AlertPolicyServiceClient.update_alert_policy() | AlertPolicyClient.UpdateAlertPolicy() |
| Delete alert policy | DELETE /v3/{name} | AlertPolicyServiceClient.delete_alert_policy() | AlertPolicyClient.DeleteAlertPolicy() |

### Notification Channels

| Goal | REST Method | Python SDK | Go SDK |
|------|------------|-----------|--------|
| List channels | GET /v3/{name}/notificationChannels | NotificationChannelServiceClient.list_notification_channels() | NotificationChannelClient.ListNotificationChannels() |
| Get channel | GET /v3/{name} | NotificationChannelServiceClient.get_notification_channel() | NotificationChannelClient.GetNotificationChannel() |
| Create channel | POST /v3/{name}/notificationChannels | NotificationChannelServiceClient.create_notification_channel() | NotificationChannelClient.CreateNotificationChannel() |
| Update channel | PATCH /v3/{name} | NotificationChannelServiceClient.update_notification_channel() | NotificationChannelClient.UpdateNotificationChannel() |
| Delete channel | DELETE /v3/{name} | NotificationChannelServiceClient.delete_notification_channel() | NotificationChannelClient.DeleteNotificationChannel() |
| Send verification | POST /v3/{name}:sendVerificationCode | NotificationChannelServiceClient.send_notification_channel_verification_code() | NotificationChannelClient.SendNotificationChannelVerificationCode() |

### Dashboards

| Goal | REST Method | Python SDK | Go SDK |
|------|------------|-----------|--------|
| List dashboards | GET /v3/{name}/dashboards | DashboardsServiceClient.list_dashboards() | DashboardClient.ListDashboards() |
| Get dashboard | GET /v3/{name} | DashboardsServiceClient.get_dashboard() | DashboardClient.GetDashboard() |
| Create dashboard | POST /v3/{name}/dashboards | DashboardsServiceClient.create_dashboard() | DashboardClient.CreateDashboard() |
| Update dashboard | PATCH /v3/{name} | DashboardsServiceClient.update_dashboard() | DashboardClient.UpdateDashboard() |
| Delete dashboard | DELETE /v3/{name} | DashboardsServiceClient.delete_dashboard() | DashboardClient.DeleteDashboard() |

### Uptime Checks

| Goal | REST Method | Python SDK | Go SDK |
|------|------------|-----------|--------|
| List uptime checks | GET /v3/{name}/uptimeCheckConfigs | UptimeCheckServiceClient.list_uptime_check_configs() | UptimeCheckClient.ListUptimeCheckConfigs() |
| Get uptime check | GET /v3/{name} | UptimeCheckServiceClient.get_uptime_check_config() | UptimeCheckClient.GetUptimeCheckConfig() |
| Create uptime check | POST /v3/{name}/uptimeCheckConfigs | UptimeCheckServiceClient.create_uptime_check_config() | UptimeCheckClient.CreateUptimeCheckConfig() |
| Update uptime check | PATCH /v3/{name} | UptimeCheckServiceClient.update_uptime_check_config() | UptimeCheckClient.UpdateUptimeCheckConfig() |
| Delete uptime check | DELETE /v3/{name} | UptimeCheckServiceClient.delete_uptime_check_config() | UptimeCheckClient.DeleteUptimeCheckConfig() |
| List uptime check IPs | GET /v3/uptimeCheckIps | UptimeCheckServiceClient.list_uptime_check_ips() | UptimeCheckClient.ListUptimeCheckIps() |

## Key JSON Paths (Centralized)

See [SKILL.md § Common JSON Paths](../SKILL.md#common-json-paths) for full path reference.

## Pagination Pattern

### Python SDK

```python
# list_time_series uses pages automatically
for page in client.list_time_series(request).pages:
    for ts in page.time_series:
        process(ts)

# List-based services: use .pages or iterate directly
for page in client.list_alert_policies(request).pages:
    for policy in page.alert_policies:
        process(policy)
```

### Go SDK

```go
it := client.ListAlertPolicies(ctx, req)
for {
    policy, err := it.Next()
    if err == iterator.Done { break }
    if err != nil { log.Fatalf("Next: %v", err) }
    process(policy)
}
```

### REST API (curl)

```bash
# First page
curl -s "https://monitoring.googleapis.com/v3/projects/$PROJECT/alertPolicies?pageSize=100"

# Subsequent pages with nextPageToken
curl -s "https://monitoring.googleapis.com/v3/projects/$PROJECT/alertPolicies?pageSize=100&pageToken=$NEXT_TOKEN"
```

## Error Handling

| gRPC Code | HTTP | Monitoring-Specific Action |
|-----------|------|---------------------------|
| `INVALID_ARGUMENT` | 400 | Fix filter syntax, metric type, or resource path |
| `PERMISSION_DENIED` | 403 | Grant monitoring.* IAM role |
| `NOT_FOUND` | 404 | Resource does not exist; list to find correct ID |
| `ALREADY_EXISTS` | 409 | Use descriptive name + project-unique IDs |
| `DEADLINE_EXCEEDED` | 504 | Reduce query scope (shorter interval, narrower filter) |
| `UNAVAILABLE` | 503 | Backoff retry (5s, 10s, 20s) |
| `INTERNAL` | 500 | Retry (2s, 4s, 8s); then escalate |
| `QUOTA_EXCEEDED` | 429 | Reduce request rate or delete unused resources |

## Filter Syntax

Monitoring filter language examples:

```
# Metric type
metric.type = "compute.googleapis.com/instance/cpu/utilization"

# Resource type + metric type
resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"

# Label filter
metric.type = "compute.googleapis.com/instance/cpu/utilization" AND metric.labels.instance_name = "my-vm"

# Aggregation filter (alert policies)
resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"

# Log-based metric filter
resource.type = "global" AND metric.type = "logging.googleapis.com/user/my_counter"
```
