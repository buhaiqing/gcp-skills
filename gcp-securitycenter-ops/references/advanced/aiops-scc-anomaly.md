# SCC Advanced Monitoring & AIOps

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Finding Anomaly Detection](#finding-anomaly-detection)
- [Threat Pattern Analysis](#threat-pattern-analysis)
- [Anomaly Alert Configuration](#anomaly-alert-configuration)
- [Automated Triage](#automated-triage)
- [Best Practices](#best-practices)

---

## Overview

This guide covers advanced AIOps patterns for Security Command Center including anomaly detection for security findings, threat pattern analysis, and automated triage using Cloud Monitoring, Pub/Sub, and custom integrations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  SCC AIOps Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  SCC        │    │  Pub/Sub    │    │  Cloud      │        │
│  │  Findings   │───►│  Topic      │───►│  Logging    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Anomaly    │    │  Pattern    │    │  Alert      │        │
│  │  Detection  │    │  Analysis   │    │  System     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                │
│                            ▼                                   │
│                   ┌─────────────┐                              │
│                   │  Auto-Triage│                              │
│                   │  + Response │                              │
│                   └─────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable securitycenter.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# Required IAM roles
# - roles/securitycenter.admin (manage findings)
# - roles/pubsub.publisher (publish notifications)
# - roles/monitoring.editor (create alerts)
# - roles/logging.viewer (query logs)
```

## Finding Anomaly Detection

### Query SCC Findings

```bash
# List active findings
gcloud scc findings list organizations/ORG_ID/sources/SOURCE_ID \
  --filter="state=\"ACTIVE\""

# List findings by severity
gcloud scc findings list organizations/ORG_ID/sources/SOURCE_ID \
  --filter="state=\"ACTIVE\" AND severity=\"HIGH\""

# List findings by category
gcloud scc findings list organizations/ORG_ID/sources/SOURCE_ID \
  --filter="state=\"ACTIVE\" AND category=\"Persistence: Persistent Disk Snapshot Created\""
```

### Detect Finding Anomalies

```python
# Python SDK for anomaly detection
from google.cloud import securitycenter_v1
from datetime import datetime, timedelta

def detect_finding_anomalies(org_id, source_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    # Query findings from last 24 hours
    start_time = datetime.utcnow() - timedelta(hours=24)
    
    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": f"eventTime >= \"{start_time.isoformat()}Z\""
        }
    )
    
    # Analyze finding patterns
    category_counts = {}
    for finding in findings:
        category = finding.finding.category
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Detect anomalies (categories with > 2x average)
    avg_count = sum(category_counts.values()) / len(category_counts)
    anomalies = {k: v for k, v in category_counts.items() if v > avg_count * 2}
    
    return anomalies
```

### Monitor Finding Velocity

```python
# Detect sudden spike in findings
def detect_finding_velocity(org_id, source_id):
    from google.cloud import securitycenter_v1
    from datetime import datetime, timedelta
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    # Compare last hour vs previous hour
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)
    
    # Count findings in last hour
    recent_findings = client.list_findings(
        request={
            "parent": parent,
            "filter": f"eventTime >= \"{hour_ago.isoformat()}Z\" AND eventTime < \"{now.isoformat()}Z\""
        }
    )
    
    # Count findings in previous hour
    previous_findings = client.list_findings(
        request={
            "parent": parent,
            "filter": f"eventTime >= \"{two_hours_ago.isoformat()}Z\" AND eventTime < \"{hour_ago.isoformat()}Z\""
        }
    )
    
    recent_count = len(list(recent_findings))
    previous_count = len(list(previous_findings))
    
    # Detect velocity anomaly (> 3x increase)
    if previous_count > 0 and recent_count > previous_count * 3:
        return {
            "anomaly": True,
            "recent": recent_count,
            "previous": previous_count,
            "multiplier": recent_count / previous_count
        }
    
    return {"anomaly": False}
```

## Threat Pattern Analysis

### Analyze Finding Sources

```python
# Analyze which sources are generating most findings
def analyze_finding_sources(org_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    sources = client.list_sources(request={"parent": parent})
    
    source_analysis = {}
    for source in sources:
        findings = client.list_findings(
            request={"parent": source.name}
        )
        
        finding_count = len(list(findings))
        source_analysis[source.display_name] = {
            "count": finding_count,
            "id": source.name.split("/")[-1]
        }
    
    return source_analysis
```

### Detect Threat Patterns

```python
# Detect patterns in threat categories
def detect_threat_patterns(org_id, source_id, days=7):
    from google.cloud import securitycenter_v1
    from datetime import datetime, timedelta
    from collections import Counter
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    start_time = datetime.utcnow() - timedelta(days=days)
    
    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": f"eventTime >= \"{start_time.isoformat()}Z\""
        }
    )
    
    # Analyze patterns
    categories = Counter()
    resources = Counter()
    
    for finding in findings:
        categories[finding.finding.category] += 1
        resources[finding.finding.resource_name] += 1
    
    # Identify hotspots
    return {
        "top_categories": categories.most_common(10),
        "top_resources": resources.most_common(10)
    }
```

## Anomaly Alert Configuration

### Create Anomaly Detection Alert

```bash
# Create alert for finding velocity
gcloud alpha monitoring policies create \
  --display-name="SCC Finding Velocity Alert" \
  --condition-display-name="Finding Count > 100/hour" \
  --condition-filter='resource.type="pubsub_topic" AND metric.type="pubsub.googleapis.com/topic/message_count"' \
  --condition-threshold-value=100 \
  --condition-threshold-duration=3600s \
  --notification-channels=CHANNEL_ID
```

### Create Severity-based Alert

```bash
# Create alert for high-severity findings
gcloud alpha monitoring policies create \
  --display-name="SCC High Severity Alert" \
  --condition-display-name="High Severity Finding" \
  --condition-filter='resource.type="securitycenter.googleapis.com/Finding" AND metric.type="securitycenter.googleapis.com/finding/count"' \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s \
  --notification-channels=CHANNEL_ID
```

## Automated Triage

### Auto-mute Low-Severity Findings

```python
# Auto-mute low-severity findings
def auto_mute_low_severity(org_id, source_id, mute_config_id):
    from google.cloud import securitycenter_v1
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": "state=\"ACTIVE\" AND severity=\"LOW\""
        }
    )
    
    for finding in findings:
        # Mute the finding
        client.update_finding(
            request={
                "finding": {
                    "name": finding.name,
                    "mute": "MUTED"
                }
            }
        )
```

### Auto-close Stale Findings

```python
# Auto-close findings older than 30 days
def auto_close_stale_findings(org_id, source_id, days=30):
    from google.cloud import securitycenter_v1
    from datetime import datetime, timedelta
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": f"state=\"ACTIVE\" AND eventTime < \"{cutoff_date.isoformat()}Z\""
        }
    )
    
    for finding in findings:
        # Mark as inactive
        client.update_finding(
            request={
                "finding": {
                    "name": finding.name,
                    "state": "INACTIVE"
                }
            }
        )
```

## Best Practices

1. **Baseline Metrics**: Establish baselines for finding velocity before setting thresholds
2. **Multi-factor Alerts**: Combine finding count, severity, and category for comprehensive detection
3. **Noise Reduction**: Use mute configs for known acceptable findings
4. **Regular Review**: Review anomalies weekly to refine detection rules
5. **Integration**: Integrate with SIEM/SOAR for automated response
6. **Documentation**: Document known anomalies vs. real threats

## See Also

- [SCC Notifications](https://cloud.google.com/security-command-center/docs/concepts-notification-config)
- [SCC API Reference](https://cloud.google.com/security-command-center/docs/reference/rest)
