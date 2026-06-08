# Core Concepts — Cloud Monitoring

## Architecture

Google Cloud Monitoring (formerly Stackdriver) collects, stores, and analyzes metrics from Google Cloud resources, hybrid environments, and application code — enabling observability through metrics, alerts, dashboards, uptime checks, and service-level objectives (SLOs).

### Metric Types

| Type | Description | Reset Behavior | Example |
|------|-------------|----------------|---------|
| **gauge** | Point-in-time measurement | N/A | CPU utilization %, memory used bytes |
| **cumulative** | Monotonically increasing counter | Resets on restart | Total request count, bytes egress |
| **delta** | Change over an interval | Resets each interval | Requests per second, bytes per second |

### Monitored Resources

| Resource Type | Description | Key Labels |
|---------------|-------------|------------|
| `gce_instance` | Compute Engine VM | instance_id, zone |
| `k8s_container` | GKE container | cluster_name, namespace_name, container_name |
| `cloudsql_database` | Cloud SQL instance | database_id, region |
| `global` | Non-resource metrics | project_id |
| `generic_task` | Custom external service | location, namespace, job, task_id |

### Metric Domains

| Domain | Prefix | Coverage |
|--------|--------|----------|
| Compute Engine | `compute.googleapis.com` | CPU, disk, network, instance lifecycle |
| Cloud SQL | `cloudsql.googleapis.com` | CPU, memory, connections, replication, storage |
| GKE | `kubernetes.io`, `k8s.io` | Pods, nodes, deployments, HPA metrics |
| Cloud Storage | `storage.googleapis.com` | Bucket size, object count, operations, bandwidth |
| BigQuery | `bigquery.googleapis.com` | Query slots, bytes processed, job count |
| Load Balancing | `loadbalancing.googleapis.com` | Backend latency, healthy backends, request count |
| Custom | `custom.googleapis.com` / `external.googleapis.com` | User-defined metrics |

### Custom Metrics

| Method | Use Case | Limits |
|--------|----------|--------|
| Monitoring API `createMetricDescriptor` | Application metrics | 1,000 descriptors per project (auto-created on first write) |
| OpenTelemetry SDK | Instrumented app metrics | Same limits; structured labels |
| Log-based metrics | Derive from log entries | Extract numeric or distribution values from logs |

### Retention Periods

| Metric Category | Retention |
|-----------------|-----------|
| Standard Google Cloud metrics | 6 weeks |
| Custom metrics (standard) | 6 weeks |
| Custom metrics (premium) | Per pricing tier (up to 24 months) |
| Uptime check results | 30 days |
| Alert policy history | 90 days |

### Quotas & Limits

| Resource | Default Limit |
|----------|--------------|
| Alert policies per project | 5,000 |
| Notification channels per project | 500 |
| Dashboards per project | 5,000 |
| Uptime check configs per project | 100 |
| Custom metric descriptors | 1,000 per project |
| Custom metrics data points per minute | 500,000 (standard), higher with premium |
| Time series queried per request | 10,000 |
| Alert policy mutations per minute | 100 |

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| Monitoring API enabled | `monitoring.googleapis.com` must be enabled on the project |
| Service account permissions | `roles/monitoring.viewer` (read), `roles/monitoring.editor` (write), `roles/monitoring.admin` (full) |
| Network access | Outbound to `monitoring.googleapis.com` (TCP 443) |
| Project billing enabled | Required for custom metrics and premium features |
