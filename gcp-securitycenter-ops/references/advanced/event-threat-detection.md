# Event Threat Detection — Deep Dive

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [ETD Detector Configuration](#etd-detector-configuration)
- [Custom Threat Detection](#custom-threat-detection)
- [Finding Management](#finding-management)
- [Integration with SIEM](#integration-with-siem)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Event Threat Detection (ETD) is a SCC Premium/Enterprise feature that provides real-time threat detection using Google's threat intelligence. This guide covers advanced ETD configuration, custom threat detection, and integration patterns.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               Event Threat Detection Architecture               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Cloud      │    │  ETD        │    │  SCC        │        │
│  │  Logging    │───►│  Detectors  │───►│  Findings   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Audit      │    │  Threat     │    │  Pub/Sub    │        │
│  │  Logs       │    │  Intel      │    │  Alerts     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable securitycenter.googleapis.com
gcloud services enable logging.googleapis.com

# Required IAM roles
# - roles/securitycenter.admin (manage ETD)
# - roles/logging.viewer (read logs)
# - roles/securitycenter.findingsEditor (manage findings)
```

## ETD Detector Configuration

### List Available Detectors

```bash
# List all ETD detectors
gcloud scc settings get organizations/ORG_ID \
  --format="value(detectors)"

# List enabled detectors
gcloud scc settings get organizations/ORG_ID \
  --format="value(detectors[].enabled)"
```

### Enable/Disable Detectors

```bash
# Enable a specific detector
gcloud scc settings update organizations/ORG_ID \
  --update-detector=DETECTOR_NAME \
  --enable

# Disable a specific detector
gcloud scc settings update organizations/ORG_ID \
  --update-detector=DETECTOR_NAME \
  --disable
```

### Configure Detector Filters

```bash
# Add filter to detector
gcloud scc settings update organizations/ORG_ID \
  --update-detector=DETECTOR_NAME \
  --filter="resource.type=gce_instance"

# Remove filter
gcloud scc settings update organizations/ORG_ID \
  --update-detector=DETECTOR_NAME \
  --remove-filter
```

## Custom Threat Detection

### Create Custom Detection Rule

```python
# Python SDK for custom detection
from google.cloud import securitycenter_v1

def create_custom_detection(org_id, source_id, detection_config):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    # Create custom finding
    finding = securitycenter_v1.Finding(
        category=detection_config["category"],
        state="ACTIVE",
        severity=detection_config["severity"],
        resource_name=detection_config["resource_name"],
        event_time=detection_config["event_time"],
        source_properties=detection_config["properties"]
    )
    
    response = client.create_finding(
        request={
            "parent": parent,
            "finding_id": detection_config["finding_id"],
            "finding": finding
        }
    )
    
    return response
```

### Query Custom Findings

```bash
# List custom findings
gcloud scc findings list organizations/ORG_ID/sources/SOURCE_ID \
  --filter="category=\"Custom:Anomalous Access Pattern\""

# List findings with custom properties
gcloud scc findings list organizations/ORG_ID/sources/SOURCE_ID \
  --filter="sourceProperties.anomalyScore > 0.8"
```

## Finding Management

### Update Finding State

```bash
# Mark finding as inactive
gcloud scc findings update organizations/ORG_ID/sources/SOURCE_ID/findings/FINDING_ID \
  --update-mask=state \
  --state=INACTIVE

# Mute finding
gcloud scc findings update organizations/ORG_ID/sources/SOURCE_ID/findings/FINDING_ID \
  --update-mask=mute \
  --mute=MUTED
```

### Add Finding Attributes

```bash
# Add source properties
gcloud scc findings update organizations/ORG_ID/sources/SOURCE_ID/findings/FINDING_ID \
  --update-mask=sourceProperties \
  --source-properties=" analystNotes:STRING_VALUE:Initial analysis by SOC team"
```

## Integration with SIEM

### Export to Splunk

```python
# Export findings to Splunk
def export_to_splunk(finding, splunk_url, splunk_token):
    import requests
    
    payload = {
        "event": finding.category,
        "source": "SCC",
        "sourcetype": "scc_findings",
        "fields": {
            "resource_name": finding.resource_name,
            "severity": finding.severity,
            "state": finding.state,
            "event_time": finding.event_time.isoformat()
        }
    }
    
    headers = {
        "Authorization": f"Splunk {splunk_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{splunk_url}/services/collector", json=payload, headers=headers)
    return response.status_code
```

### Export to Chronicle

```python
# Export findings to Chronicle
def export_to_chronicle(finding, chronicle_url, chronicle_token):
    import requests
    
    payload = {
        "events": [{
            "log_type": "SCC_FINDING",
            "log_text": str(finding)
        }]
    }
    
    headers = {
        "Authorization": f"Bearer {chronicle_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{chronicle_url}/v1/logs:import", json=payload, headers=headers)
    return response.status_code
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No findings generated | ETD not enabled | Check: `gcloud scc settings get organizations/ORG_ID` |
| Findings delayed | Log export latency | Verify: Cloud Logging export to SCC |
| False positives | Overly broad detection | Add filters: `gcloud scc settings update` |
| Missing attributes | Source properties not logged | Update detection rule to include properties |

### Verify ETD Configuration

```bash
# Check ETD status
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(detectors)"

# Check detector details
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(detectors[?name=='DETECTOR_NAME'])"
```

## Best Practices

1. **Enable Key Detectors**: Enable detectors for critical attack vectors
2. **Custom Filters**: Use filters to reduce noise from known exceptions
3. **Regular Review**: Review and tune detection rules monthly
4. **Integration**: Connect ETD to SIEM for centralized monitoring
5. **Documentation**: Document custom detections and their purpose
6. **Testing**: Test detection rules with known attack patterns

## See Also

- [Event Threat Detection](https://cloud.google.com/security-command-center/docs/concepts-event-threat-detection)
- [ETD Detectors](https://cloud.google.com/security-command-center/docs/reference/rest/v1/organizations.settings.detectorConfigs)
