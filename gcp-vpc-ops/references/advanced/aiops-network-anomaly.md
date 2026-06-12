# AIOps Anomaly Detection — Google Cloud VPC

> Provides network administrators with a guide to implementing AIOps-driven anomaly detection for VPC networking — flow log analysis, connectivity anomaly detection, real-time alerting, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Enabling VPC Flow Logs](#enabling-vpc-flow-logs)
5. [Log-Based Anomaly Detection](#log-based-anomaly-detection)
6. [Cloud Monitoring Insights](#cloud-monitoring-insights)
7. [BigQuery ML for Anomaly Detection](#bigquery-ml-for-anomaly-detection)
8. [Real-Time Alerting](#real-time-alerting)
9. [Automated Remediation](#automated-remediation)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Cost Optimization](#cost-optimization)
13. [See Also](#see-also)

## Overview

AIOps (Artificial Intelligence for IT Operations) uses machine learning and data analysis to detect anomalies in VPC network traffic. With VPC Flow Logs, you can:

- Detect unexpected traffic spikes (potential DDoS or data exfiltration)
- Identify connectivity anomalies (dropped connections, high latency)
- Monitor port scanning or reconnaissance activity
- Track unusual data transfer patterns (cost anomalies)
- Automate remediation responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Traffic spike | Volume threshold + ML baseline | High |
| Port scanning | Multiple destination ports from single source | Medium |
| Data exfiltration | Unexpected egress to unknown IPs | Critical |
| Connection failures | High ratio of RST packets | Medium |
| Latency increase | Flow log RTT metrics | Low |
| Unusual protocols | Protocol distribution shift | Medium |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Data Pipeline                                  │
│                                                                          │
│  VPC Flow Logs                                                          │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ VM/GKE Pods    │───►│ Cloud Logging  │───►│ Log Router / Sink   │   │
│  │ (Network Flows) │    │ (Log Explorer) │    │ (Export Destination)│   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ BigQuery    │      │ Pub/Sub     │     │ Cloud       │        │
│       │ (ML Models) │      │ (Streaming) │     │ Storage     │        │
│       └─────────────┘      └──────┬──────┘     │ (Archive)   │        │
│                                   │             └─────────────┘        │
│                            ┌──────▼──────┐                            │
│                            │ Cloud       │                            │
│                            │ Functions   │                            │
│                            │ (Analysis)  │                            │
│                            └──────┬──────┘                            │
│                                   │                                    │
│                            ┌──────▼──────┐                            │
│                            │ Cloud       │                            │
│                            │ Monitoring  │                            │
│                            │ (Alerting)  │                            │
│                            └─────────────┘                            │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Compute API enabled | `gcloud services list --enabled --filter="name:compute.googleapis.com"` | Enabled | `gcloud services enable compute.googleapis.com` |
| Logging enabled | `gcloud services list --enabled --filter="name:logging.googleapis.com"` | Enabled | `gcloud services enable logging.googleapis.com` |
| BigQuery enabled | `gcloud services list --enabled --filter="name:bigquery.googleapis.com"` | Enabled | `gcloud services enable bigquery.googleapis.com` |
| Monitoring enabled | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | `gcloud services enable monitoring.googleapis.com` |

## Enabling VPC Flow Logs

### Enable for Subnet

```bash
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --enable-flow-logs \
  --logging-aggregation-interval=INTERVAL_5_SEC \
  --logging-flow-sampling=1.0 \
  --logging-metadata=INCLUDE_ALL_METADATA
```

### Verify Flow Logs

```bash
# Check subnet configuration
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --format="json" | jq '{enableFlowLogs, logConfig}'

# View recent flow logs
gcloud logging read \
  "resource.type=gce_subnetwork AND resource.labels.subnetwork_name={{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=10 \
  --format=json
```

## Log-Based Anomaly Detection

### Query for Traffic Spikes

```sql
-- BigQuery: Detect traffic spikes (>2x standard deviation)
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
  COUNT(*) AS flow_count,
  SUM(CASE WHEN bytes_sent IS NOT NULL THEN bytes_sent ELSE 0 END) AS total_bytes_sent,
  SUM(CASE WHEN bytes_received IS NOT NULL THEN bytes_received ELSE 0 END) AS total_bytes_received
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.vpc_flows`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY hour
ORDER BY hour DESC
```

### Query for Port Scanning

```sql
-- BigQuery: Detect potential port scanning
SELECT
  src_ip,
  COUNT(DISTINCT dest_port) AS unique_ports,
  COUNT(*) AS total_flows,
  TIMESTAMP_TRUNC(MIN(timestamp), HOUR) AS first_seen,
  TIMESTAMP_TRUNC(MAX(timestamp), HOUR) AS last_seen
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.vpc_flows`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND dest_port BETWEEN 1 AND 65535
GROUP BY src_ip
HAVING unique_ports > 100
ORDER BY unique_ports DESC
```

### Query for Data Exfiltration

```sql
-- BigQuery: Detect large egress to new destinations
SELECT
  dest_ip,
  COUNT(*) AS flow_count,
  SUM(bytes_sent) AS total_bytes_sent,
  MIN(timestamp) AS first_seen,
  MAX(timestamp) AS last_seen
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.vpc_flows`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND dest_ip NOT IN (
    SELECT dest_ip FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.known_destinations`
  )
GROUP BY dest_ip
HAVING total_bytes_sent > 1000000000  -- 1GB
ORDER BY total_bytes_sent DESC
```

### Query for Connection Failures

```sql
-- BigQuery: Detect high ratio of RST/ACK packets (connection failures)
SELECT
  src_ip,
  dest_ip,
  dest_port,
  COUNTIF(packet_direction = 'EGRESS' AND packets_sent = 0) AS failed_connections,
  COUNT(*) AS total_connections,
  SAFE_DIVIDE(
    COUNTIF(packet_direction = 'EGRESS' AND packets_sent = 0),
    COUNT(*)
  ) AS failure_ratio
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.vpc_flows`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY src_ip, dest_ip, dest_port
HAVING failure_ratio > 0.5
ORDER BY failed_connections DESC
```

## Cloud Monitoring Insights

### Create Alert Policy

```bash
# Create alert for traffic spike
gcloud alpha monitoring policies create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --policy='{
    "displayName": "VPC Traffic Spike Alert",
    "conditions": [{
      "displayName": "Traffic spike",
      "conditionThreshold": {
        "filter": "metric.type=\"logging.googleapis.com/user/vpc_traffic_bytes\" AND resource.type=\"gce_subnetwork\"",
        "aggregations": [{
          "alignmentPeriod": "300s",
          "crossSeriesReducer": "REDUCE_NONE",
          "perSeriesAligner": "ALIGN_MEAN"
        }],
        "comparison": "COMPARISON_GT",
        "duration": "0s",
        "thresholdValue": 1000000000,
        "trigger": {
          "count": 1
        }
      }
    }],
    "alertStrategy": {
      "autoClose": "1800s"
    },
    "combiner": "OR",
    "notificationChannels": ["projects/{{env.CLOUDSDK_CORE_PROJECT}}/notificationChannels/{{user.channel_id}}"]
  }'
```

### Create Uptime Check

```bash
# Create uptime check for network connectivity
gcloud monitoring uptime-check create "vpc-connectivity-check" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --host="{{user.endpoint_ip}}" \
  --http-check \
  --path="/health" \
  --port=443 \
  --period=60 \
  --timeout=10 \
  --expect-content="OK"
```

## BigQuery ML for Anomaly Detection

### Create ML Model

```sql
-- Create ML model for anomaly detection
CREATE OR REPLACE MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.traffic_anomaly_detector`
OPTIONS(
  model_type='ARIMA_PLUS',
  time_series_timestamp_col='timestamp',
  time_series_data_col='bytes_sent',
  time_series_id_col='src_ip'
) AS
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS timestamp,
  src_ip,
  SUM(bytes_sent) AS bytes_sent
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.vpc_flows`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY timestamp, src_ip;
```

### Detect Anomalies with ML

```sql
-- Use ML model to detect anomalies
SELECT
  timestamp,
  src_ip,
  bytes_sent,
  predicted_bytes_sent,
  prediction_interval_lower_bound,
  prediction_interval_upper_bound,
  CASE
    WHEN bytes_sent > prediction_interval_upper_bound THEN 'ANOMALY_HIGH'
    WHEN bytes_sent < prediction_interval_lower_bound THEN 'ANOMALY_LOW'
    ELSE 'NORMAL'
  END AS anomaly_type
FROM
  ML.FORECAST(
    MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.traffic_anomaly_detector`,
    STRUCT(24 AS horizon, 0.95 AS confidence_level)
  )
ORDER BY timestamp DESC
```

### Automated Anomaly Detection Script

```python
# detect_anomalies.py — Run daily via Cloud Scheduler
from google.cloud import bigquery
import smtplib
from email.mime.text import MIMEText

project = os.environ["CLOUDSDK_CORE_PROJECT"]
dataset = "network_analytics"

def detect_anomalies():
    client = bigquery.Client(project=project)
    
    query = f"""
    SELECT
      src_ip,
      dest_ip,
      dest_port,
      SUM(bytes_sent) AS total_bytes,
      COUNT(*) AS flow_count,
      MAX(timestamp) AS last_seen
    FROM `{project}.{dataset}.vpc_flows`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    GROUP BY src_ip, dest_ip, dest_port
    HAVING total_bytes > 1000000000  # 1GB in 1 hour
    """
    
    results = client.query(query).result()
    
    anomalies = []
    for row in results:
        anomalies.append({
            'src_ip': row.src_ip,
            'dest_ip': row.dest_ip,
            'dest_port': row.dest_port,
            'total_bytes': row.total_bytes,
            'flow_count': row.flow_count
        })
    
    if anomalies:
        # Send alert
        send_alert(anomalies)
        print(f"Found {len(anomalies)} anomalies")
    else:
        print("No anomalies detected")

def send_alert(anomalies):
    msg = MIMEText(f"Anomalies detected: {len(anomalies)}")
    # Configure email/webhook notification here

if __name__ == "__main__":
    detect_anomalies()
```

## Real-Time Alerting

### Pub/Sub + Cloud Function Pipeline

```bash
# Create Pub/Sub topic for flow log events
gcloud pubsub topics create "vpc-anomaly-alerts" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Create log sink to Pub/Sub
gcloud logging sinks create "vpc-flow-anomaly-sink" \
  pubsub.googleapis.com/projects/{{env.CLOUDSDK_CORE_PROJECT}}/topics/vpc-anomaly-alerts \
  --log-filter='resource.type="gce_subnetwork" AND jsonPayload.bytes_sent > 1000000000' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Cloud Function for Alert Processing

```python
# process_anomaly.py — Deploy as Cloud Function
import json
import base64
import os
from google.cloud import monitoring_v3

def process_anomaly(event, context):
    """Triggered by Pub/Sub message from flow log anomaly."""
    data = base64.b64decode(event['data']).decode('utf-8')
    flow_log = json.loads(data)
    
    # Extract anomaly details
    src_ip = flow_log.get('jsonPayload', {}).get('src_ip')
    dest_ip = flow_log.get('jsonPayload', {}).get('dest_ip')
    bytes_sent = flow_log.get('jsonPayload', {}).get('bytes_sent', 0)
    
    # Create monitoring alert
    client = monitoring_v3.AlertPolicyServiceClient()
    project_name = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}"
    
    # Create incident in Cloud Monitoring
    print(f"Anomaly detected: {src_ip} -> {dest_ip}: {bytes_sent} bytes")
    
    # Trigger automated response
    if bytes_sent > 10000000000:  # 10GB
        trigger_remediation(src_ip, dest_ip)

def trigger_remediation(src_ip, dest_ip):
    """Create firewall rule to block anomalous traffic."""
    # Implement firewall rule creation logic
    print(f"Blocking traffic from {src_ip} to {dest_ip}")
```

## Automated Remediation

### Cloud Function + Firewall Rule

```python
# auto_remediate.py — Block anomalous source IPs
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
firewall_client = compute_v1.FirewallsClient()

def block_anomalous_ip(src_ip, network_name):
    rule_name = f"block-anomaly-{src_ip.replace('.', '-')}"
    
    rule = compute_v1.Firewall()
    rule.name = rule_name
    rule.network = f"https://www.googleapis.com/compute/v1/projects/{project}/global/networks/{network_name}"
    rule.direction = "INGRESS"
    rule.priority = 1000  # Higher priority than allow rules
    rule.source_ranges = [src_ip]
    rule.denied = [{"IPProtocol": "all"}]
    
    op = firewall_client.insert(project=project, firewall_resource=rule)
    op.result()  # Wait for completion
    
    print(f"Blocked IP {src_ip} via rule {rule_name}")
```

### Automated Cloud NAT Cleanup

```python
# auto_cleanup_nat.py — Remove NAT during off-peak hours
from google.cloud import compute_v1
from datetime import datetime, timezone

project = os.environ["CLOUDSDK_CORE_PROJECT"]
nats_client = compute_v1.RouterNatsClient()

def auto_cleanup_nat(region, router_name, nat_name):
    current_hour = datetime.now(timezone.utc).hour
    
    # Delete NAT during weekends or off-peak hours
    if current_hour >= 20 or current_hour <= 6:
        op = nats_client.delete(
            project=project,
            region=region,
            router=router_name,
            nat=nat_name
        )
        print(f"NAT {nat_name} deleted for off-peak cost savings")
```

## Best Practices

### Data Pipeline Design

| Stage | Tool | Purpose |
|-------|------|---------|
| Collection | VPC Flow Logs | Capture network flows |
| Ingestion | Cloud Logging | Centralized log storage |
| Processing | Cloud Function / Dataflow | Real-time analysis |
| Storage | BigQuery / Cloud Storage | Historical analysis |
| ML Training | BigQuery ML / Vertex AI | Anomaly model training |
| Alerting | Cloud Monitoring | Real-time notifications |
| Remediation | Cloud Function | Automated response |

### Sampling Strategy

| Environment | Sampling Rate | Aggregation Interval |
|-------------|---------------|---------------------|
| Production (critical) | 1.0 (100%) | 5 seconds |
| Production (standard) | 0.5 (50%) | 30 seconds |
| Staging | 0.25 (25%) | 60 seconds |
| Development | 0.1 (10%) | 300 seconds |

### Alert Thresholds

| Anomaly Type | Threshold | Severity |
|--------------|-----------|----------|
| Traffic spike | >3x baseline | P1 |
| Port scanning | >100 ports/min from single IP | P2 |
| Data exfiltration | >1GB to new destination | P1 |
| Connection failure | >50% failure ratio | P2 |
| Latency increase | >200ms average | P3 |

## Troubleshooting

### Issue: Flow logs delayed

**Diagnosis:**
```bash
# Check log ingestion latency
gcloud logging read \
  "resource.type=gce_subnetwork AND jsonPayload.bytes_sent > 0" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=5 \
  --format="json" | jq '.[].timestamp'
```

**Solution:** Increase sampling rate or reduce aggregation interval.

### Issue: False positives

**Diagnosis:**
```bash
# Review anomaly detection thresholds
gcloud logging read \
  "resource.type=gce_subnetwork AND jsonPayload.bytes_sent > 1000000000" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=100
```

**Solution:** Tune thresholds based on historical baseline data.

### Issue: Missing logs for specific VM

**Diagnosis:**
```bash
# Check subnet flow log configuration
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --format="json" | jq '.enableFlowLogs'
```

**Solution:** Enable flow logs on the subnet and verify VM network interface.

### Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `Logs not appearing` | Sampling rate too low | Increase to 1.0 for critical subnets |
| `High false positive rate` | Threshold too sensitive | Increase threshold or use ML baseline |
| `BigQuery export delay` | Sink configuration issue | Verify log sink exists and is active |
| `Pub/Sub message loss` | Subscription not configured | Create subscription for the topic |
| `Cloud Function timeout` | Processing too slow | Increase function timeout or batch processing |

## Cost Optimization

### Flow Log Cost Control

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Reduce sampling rate | 30-50% | `--logging-flow-sampling=0.5` |
| Filter by subnet | 20-30% | Enable only on critical subnets |
| Aggregate intervals | 10-20% | `--logging-aggregation-interval=INTERVAL_30_SEC` |
| Archive to Cloud Storage | 40-60% | Export cold logs to storage |
| Retention period | 20-30% | Set `--log-retention=30d` instead of default 400d |

### Cost Example

```
Scenario: 10 subnets, 100GB/month flow logs, 1 NAT gateway
Before optimization:
  Flow logs: 100GB × $0.50 = $50.00
  NAT: $32.40
  Total: $82.40/month

After optimization:
  Critical subnets only (3), 50% sampling, 30GB/month
  Flow logs: 30GB × $0.50 = $15.00
  NAT: $32.40
  Total: $47.40/month
  Savings: $35.00/month (42%)
```

## See Also

- [VPC Flow Logs Documentation](https://cloud.google.com/vpc/docs/using-flow-logs)
- [Cloud Logging Documentation](https://cloud.google.com/logging/docs)
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [BigQuery ML Documentation](https://cloud.google.com/bigquery-ml/docs)
- [Cloud NAT Cost Optimization](./finops-vpc-cost.md)
- [Monitoring Reference](../monitoring.md)