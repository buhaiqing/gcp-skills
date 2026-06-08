# Well-Architected Assessment — Cloud Monitoring

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/monitoring.admin | Full Monitoring API — production management |
| roles/monitoring.editor | Alert/dashboard/channel CRUD — operations team |
| roles/monitoring.viewer | Read-only metrics and dashboards — all developers |
| roles/monitoring.notificationChannelEditor | Notification channel management only |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`

**Data Protection**:
- Custom metric data encrypted at rest (AES-256)
- In transit via HTTPS (TLS 1.2+)
- VPC Service Controls supported — restrict Monitoring API to VPC perimeter
- Log-based metrics inherit source log ACLs

**Secret Handling**:
- Notification channel credentials (Slack tokens, webhook URLs, PagerDuty keys) stored in Monitoring API — restrict access via IAM
- Prefer Cloud Secret Manager for webhook URLs, then reference from automation scripts
- Never hardcode notification channel auth tokens in scripts or dashboard JSON

**Audit Logging**:
- All Monitoring API calls logged to Cloud Audit Logs
- Alert policy mutations: `monitoring.alertPolicies.create`, `.update`, `.delete`
- Dashboard mutations: `monitoring.dashboards.create`, `.update`, `.delete`
- Query admin logs for `protoPayload.serviceName="monitoring.googleapis.com"`

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Alert redundancy | Create duplicate alert policies with different notification channels |
| Multi-region uptime checks | Configure uptime checks from ≥ 3 regions to avoid single-region false positives |
| Dead-man's switch | Alert when NO metrics arrive for N minutes (indicates agent/API failure) |
| Notification channel backup | Maintain at least 2 channels per critical alert (email + Slack/PagerDuty) |
| Alert policy export | Periodically backup alert policies to version control for DR restore |

**DR Runbook**:
1. Export current alert policies: `gcloud monitoring alert-policies list --format=json > backup.json`
2. Export notification channels: `gcloud monitoring channels list --format=json > channels.json`
3. Export dashboards: `gcloud monitoring dashboards list --format=json > dashboards.json`
4. Restore: re-create from exported JSON configs with `gcloud monitoring {resource} create`

**Failure Scenarios**:

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Monitoring API unavailable | No new metrics, alerts delayed | Metrics cached locally by agents; resume on recovery |
| Notification channel down | Alerts fire but no delivery | Multi-channel redundancy; use dead-man's switch |
| Alert policy accidentally deleted | Blind spot until recreated | Backup + automation for policy recreation |
| Custom metric descriptor limit reached | New metrics rejected | Audit and prune unused descriptors monthly |

## §3 Cost

| Metric Category | Pricing Model | Cost Optimization |
|-----------------|---------------|-------------------|
| Standard metrics | Included in GCP | No action needed |
| Custom metrics (standard) | Per 1M samples/month | Aggregate before writing; reduce write frequency |
| Custom metrics (premium) | Higher rate, longer retention | Only premium for compliance-required metrics |
| Log-based metrics | Per log bytes ingested | Filter logs at source; use sampling for high-volume logs |
| Uptime checks | Free up to 100 checks | Consolidate checks; avoid redundant endpoint checks |
| Dashboards | Free | No cost concern |

**Waste Detection**:
```bash
# Find alert policies disabled for > 30 days (potential cleanup candidates)
gcloud monitoring alert-policies list --format=json \
  | jq '.[] | select(.enabled.value == false) | {name, displayName, creationRecord}'

# Find notification channels not referenced by any alert policy
gcloud monitoring channels list --format=json | jq '[.[].name]'
gcloud monitoring alert-policies list --format=json | jq '[.[].notificationChannels[]]'
# Compare the two lists for orphaned channels
```

**Cost Controls**:
- Set custom metric write budget: monitor `custom.googleapis.com` write rate
- Use standard retention (6 weeks) unless compliance requires premium retention
- Label custom metrics with `env` and `team` for cost attribution

## §4 Efficiency

- **Batch operations**: Create multiple alert policies from a single JSON array in scripts
- **Infrastructure as Code**: Manage alert policies and dashboards via Terraform (`google_monitoring_alert_policy`, `google_monitoring_dashboard`)
- **CI/CD integration**: Validate alert policy JSON in CI before deployment; use `gcloud monitoring alert-policies create` with `--format=json` to capture IDs
- **Automation patterns**:
  - Self-healing: Alert → Cloud Function → auto-remediate → acknowledge alert
  - Auto-scaling triggers: Export Monitoring metrics to HPA via Custom Metrics API
- **Label conventions**: Use consistent labels (`service`, `environment`, `team`) across alert policies and dashboards for filtering

**Operational Efficiency Metrics**:
- Mean Time to Detect (MTTD): Time from incident start to alert firing
- Mean Time to Acknowledge (MTTA): Time from alert to human acknowledgment
- Alert-to-incident ratio: % of alerts that result in actual incidents (target > 50%)

## §5 Performance

| Aspect | Metric | Target |
|--------|--------|--------|
| Metric ingestion delay | Time from event to queryable metric | < 5 minutes (standard), < 1 minute (premium) |
| Alert evaluation interval | How often conditions are checked | 1-5 minutes (depends on condition type) |
| Dashboard load time | Time to render all widgets | < 5 seconds |
| Time series query latency | API response time for list_time_series | < 10 seconds for standard queries |
| Uptime check frequency | Minimum interval between checks | 60 seconds (standard), 10 seconds (advanced) |

**Query Performance**:
- Use `alignmentPeriod` ≥ 60s to reduce data points
- Prefer `perSeriesAligner` + `crossSeriesReducer` aggregation over raw data
- Limit `pageSize` to 100; use pagination for large result sets
- For historical analysis (> 6 weeks), export to BigQuery via Metrics Scope export

**Scale Limits**:
- Maximum alert policies: 5,000 per project
- Maximum dashboards: 5,000 per project
- Maximum uptime checks: 100 per project
- Maximum custom metric descriptors: 1,000 per project
- Maximum time series queried: 10,000 per request
