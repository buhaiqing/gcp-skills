# SCC Enterprise Tier — Specifics

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Enterprise Features](#enterprise-features)
- [Attack Path Analysis](#attack-path-analysis)
- [Chronicle Integration](#chronicle-integration)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

SCC Enterprise provides advanced security capabilities including attack path simulation, Chronicle integration, and enhanced threat intelligence. This guide covers Enterprise-specific features and configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                SCC Enterprise Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  SCC        │    │  Attack     │    │  Chronicle  │        │
│  │  Enterprise │───►│  Path       │───►│  SIEM       │        │
│  └─────────────┘    │  Analysis   │    └─────────────┘        │
│                     └─────────────┘           │                │
│                            │                  │                │
│                            ▼                  ▼                │
│                     ┌─────────────┐    ┌─────────────┐        │
│                     │  Threat     │    │  Log        │        │
│                     │  Intel      │    │  Analytics  │        │
│                     └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable securitycenter.googleapis.com
gcloud services enable chronicle.googleapis.com

# Required IAM roles
# - roles/securitycenter.admin (manage Enterprise features)
# - roles/chronicle.admin (manage Chronicle integration)
# - roles/securitycenter.findingsEditor (manage findings)
```

## Enterprise Features

### List Enterprise Features

```bash
# Check Enterprise tier status
gcloud scc settings get organizations/ORG_ID \
  --format="value(tier)"

# List Enterprise-specific features
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(enterpriseConfig)"
```

### Enable Enterprise Features

```bash
# Enable Enterprise tier
gcloud scc settings update organizations/ORG_ID \
  --enable-enterprise

# Enable specific Enterprise features
gcloud scc settings update organizations/ORG_ID \
  --enable-feature=ATTACK_PATH_SIMULATION
```

## Attack Path Analysis

### Simulate Attack Paths

```python
# Python SDK for attack path simulation
from google.cloud import securitycenter_v1

def simulate_attack_path(org_id, asset_name):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    # Simulate attack path to asset
    response = client.simulate_attack_path(
        request={
            "parent": parent,
            "asset": asset_name,
            "simulation_config": {
                "attacker_profile": "EXTERNAL_ATTACKER",
                "attack_vector": "NETWORK"
            }
        }
    )
    
    return response.attack_path
```

### Query Attack Paths

```bash
# List attack paths for an asset
gcloud scc attack-paths simulate organizations/ORG_ID \
  --asset=ASSET_NAME \
  --format="yaml(attackPaths)"

# Get attack path details
gcloud scc attack-paths describe organizations/ORG_ID \
  --attack-path=ATTACK_PATH_ID
```

### Analyze Attack Path Risks

```python
# Analyze attack path risk scores
def analyze_attack_path_risks(org_id):
    from google.cloud import securitycenter_v1
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    attack_paths = client.list_attack_paths(
        request={"parent": parent}
    )
    
    risk_analysis = []
    for path in attack_paths:
        risk_score = path.risk_score
        risk_analysis.append({
            "path_id": path.name.split("/")[-1],
            "risk_score": risk_score,
            "attacker_profile": path.attacker_profile,
            "attack_vector": path.attack_vector
        })
    
    return sorted(risk_analysis, key=lambda x: x["risk_score"], reverse=True)
```

## Chronicle Integration

### Configure Chronicle Export

```bash
# Enable Chronicle export
gcloud scc settings update organizations/ORG_ID \
  --enable-feature=CHRONICLE_EXPORT \
  --chronicle-project=CHRONICLE_PROJECT_ID

# Configure export filters
gcloud scc settings update organizations/ORG_ID \
  --chronicle-export-filter="severity=HIGH OR severity=CRITICAL"
```

### Query Chronicle Data

```python
# Query Chronicle for SCC findings
def query_chronicle_findings(chronicle_url, chronicle_token, time_range):
    import requests
    
    query = f"""
    find where metadata.log_type = "SCC_FINDING"
    and metadata.timestamp >= "{time_range['start']}"
    and metadata.timestamp <= "{time_range['end']}"
    """
    
    headers = {
        "Authorization": f"Bearer {chronicle_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{chronicle_url}/v1/rules:run",
        json={"query": query},
        headers=headers
    )
    
    return response.json()
```

### Export Findings to Chronicle

```python
# Export SCC findings to Chronicle
def export_findings_to_chronicle(org_id, source_id, chronicle_url, chronicle_token):
    from google.cloud import securitycenter_v1
    import requests
    
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}/sources/{source_id}"
    
    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": "state=\"ACTIVE\""
        }
    )
    
    headers = {
        "Authorization": f"Bearer {chronicle_token}",
        "Content-Type": "application/json"
    }
    
    exported = 0
    for finding in findings:
        payload = {
            "events": [{
                "log_type": "SCC_FINDING",
                "log_text": str(finding)
            }]
        }
        
        response = requests.post(
            f"{chronicle_url}/v1/logs:import",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            exported += 1
    
    return exported
```

## Configuration

### Enterprise Configuration

```yaml
# enterprise-config.yaml
tier: ENTERPRISE
features:
  attackPathSimulation: true
  chronicleExport: true
  threatIntelligence: true
chronicleConfig:
  projectId: CHRONICLE_PROJECT_ID
  exportFilter: "severity=HIGH OR severity=CRITICAL"
```

### Apply Configuration

```bash
# Apply Enterprise configuration
gcloud scc settings update organizations/ORG_ID \
  --update-tier=ENTERPRISE \
  --enable-feature=ATTACK_PATH_SIMULATION \
  --enable-feature=CHRONICLE_EXPORT

# Verify configuration
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(enterpriseConfig)"
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Enterprise features unavailable | Tier not Enterprise | Check: `gcloud scc settings get organizations/ORG_ID` |
| Attack path simulation fails | Missing permissions | Verify: `roles/securitycenter.admin` |
| Chronicle export failing | Chronicle API not enabled | Enable: `gcloud services enable chronicle.googleapis.com` |
| No attack paths generated | No assets configured | Add assets to SCC inventory |

### Verify Enterprise Features

```bash
# Check Enterprise status
gcloud scc settings get organizations/ORG_ID \
  --format="value(tier)"

# Check enabled features
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(features)"

# Check Chronicle connection
gcloud scc settings get organizations/ORG_ID \
  --format="yaml(chronicleConfig)"
```

## Best Practices

1. **Asset Inventory**: Ensure all assets are registered in SCC for accurate attack path analysis
2. **Risk Prioritization**: Use attack path risk scores to prioritize remediation
3. **Chronicle Integration**: Export high-severity findings to Chronicle for SIEM correlation
4. **Regular Simulation**: Run attack path simulations monthly to identify new risks
5. **Threat Intelligence**: Enable threat intelligence feeds for enhanced detection
6. **Documentation**: Document attack path findings and remediation actions

## See Also

- [SCC Enterprise](https://cloud.google.com/security-command-center/docs/concepts-scc-enterprise)
- [Attack Path Simulation](https://cloud.google.com/security-command-center/docs/how-to-simulate-attack-paths)
