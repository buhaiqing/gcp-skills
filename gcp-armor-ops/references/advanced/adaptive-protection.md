# Adaptive Protection — Google Cloud Armor

> Provides security engineers with a guide to ML-based threat detection and automatic rule deployment in Google Cloud Armor — adaptive protection configuration, threshold tuning, and alerting.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Enable Adaptive Protection](#enable-adaptive-protection)
4. [Configuration](#configuration)
5. [Threshold Tuning](#threshold-tuning)
6. [Auto-Deploy Rules](#auto-deploy-rules)
7. [Alerting](#alerting)
8. [Monitoring](#monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

Google Cloud Armor Adaptive Protection uses machine learning to:
- **Detect**: Identify DDoS attacks and emerging threats in real-time
- **Analyze**: Assess attack patterns and traffic anomalies
- **Respond**: Automatically generate and deploy protective rules
- **Alert**: Notify security teams of detected threats

### Adaptive Protection Tiers

| Tier | Detection Method | Response Time | Use Case |
|------|-----------------|---------------|----------|
| **Standard** | Rule-based ML | Manual | Basic DDoS protection |
| **Adaptive (ML)** | ML-based anomaly detection | Auto-deploy rules | Advanced threat detection |

### Supported Attack Types

| Attack Type | Detection | Auto-Block |
|-------------|-----------|------------|
| Volumetric DDoS | ✅ | ✅ |
| Protocol attacks | ✅ | ✅ |
| Application layer attacks | ✅ | ✅ |
| Bot attacks | ✅ | Manual |
| SQL injection | ✅ (via WAF) | Manual |
| XSS | ✅ (via WAF) | Manual |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Adaptive Protection Architecture                    │
│                                                                          │
│  Incoming Traffic                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     ML Detection Engine                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ Baseline   │  │ Anomaly    │  │ Threat     │               │  │
│  │  │ Learning   │  │ Detection  │  │ Scoring    │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                               │                                         │
│                    ┌──────────▼──────────┐                             │
│                    │   Threat Assessment │                             │
│                    │   (Severity Score)  │                             │
│                    └──────────┬──────────┘                             │
│                               │                                         │
│         ┌─────────────────────┼─────────────────────┐                    │
│         ▼                     ▼                     ▼                    │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐            │
│  │ Alert Only │      │ Auto-Deploy │      │   Block    │            │
│  │ (LOW)      │      │ Rules       │      │ Immediate  │            │
│  │             │      │ (MEDIUM)    │      │ (HIGH)     │            │
│  └─────────────┘      └─────────────┘      └─────────────┘            │
└────────────────────────────────────────────────────────────────────────┘
```

## Enable Adaptive Protection

### Prerequisites

```bash
# Verify required APIs
gcloud services enable compute.googleapis.com
gcloud services enable securitycenter.googleapis.com

# Set project
export CLOUDSDK_CORE_PROJECT=my-project
```

### Enable via gcloud

```bash
# Enable Adaptive Protection for a security policy
gcloud compute security-policies update {{user.policy_name}} \
  --enable-adaptive-protection \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Enable with Auto-Deploy

```bash
# Enable with auto-deployment of rules (recommended for immediate protection)
gcloud compute security-policies update {{user.policy_name}} \
  --enable-adaptive-protection \
  --adaptive-protection-auto-deploy-enabled \
  --adaptive-protection-auto-deploy-confidence-threshold=0.75 \
  --adaptive-protection-auto-deploy-impacted-baseline-threshold=0.80 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Enable via REST API

```bash
# PATCH request to enable adaptive protection
curl -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "projects/{{env.CLOUDSDK_CORE_PROJECT}}/global/securityPolicies/{{user.policy_name}}",
    "adaptiveProtectionConfig": {
      "layer7DdosDefenseConfig": {
        "enable": true,
        "autoDeployConfidenceThreshold": 0.75,
        "autoDeployImpactedBaselineThreshold": 0.80
      }
    }
  }' \
  "https://compute.googleapis.com/compute/v1/projects/{{env.CLOUDSDK_CORE_PROJECT}}/global/securityPolicies/{{user.policy_name}}"
```

## Configuration

### Adaptive Protection Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable` | `false` | Enable/disable adaptive protection |
| `autoDeployConfidenceThreshold` | `0.75` | Confidence level to auto-deploy rules (0.0-1.0) |
| `autoDeployImpactedBaselineThreshold` | `0.80` | Traffic deviation threshold (0.0-1.0) |
| `layer7DdosDefenseConfig` | — | Layer 7 DDoS defense settings |

### Configure Auto-Deploy Parameters

```bash
# Set auto-deploy confidence threshold (higher = fewer auto-deployments)
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-confidence-threshold=0.90 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Set impacted baseline threshold (traffic deviation trigger)
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-impacted-baseline-threshold=0.90 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Threshold Reference

| Threshold Level | Confidence | Impacted Baseline | Behavior |
|-----------------|------------|-------------------|----------|
| Conservative | 0.90 | 0.90 | Minimal false positives, fewer auto-blocks |
| Balanced | 0.75 | 0.80 | Default settings |
| Aggressive | 0.50 | 0.60 | More responsive, potential false positives |

## Threshold Tuning

### Understanding Thresholds

#### Confidence Threshold

Controls when auto-deployment triggers based on ML model confidence:

```bash
# High confidence (0.90+) - only certain attacks blocked
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-confidence-threshold=0.90 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Impacted Baseline Threshold

Controls when traffic is considered anomalous based on deviation from baseline:

```bash
# High threshold (0.90) - only major deviations trigger
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-impacted-baseline-threshold=0.90 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Tuning Process

1. **Baseline Period**: Allow 7-14 days for baseline learning
2. **Initial Settings**: Start with balanced settings (0.75/0.80)
3. **Monitor False Positives**: Review blocked traffic in Cloud Logging
4. **Adjust Thresholds**: Increase if false positives, decrease if missed attacks

### Tuning Commands

```bash
# Check current adaptive protection config
gcloud compute security-policies describe {{user.policy_name}} \
  --format="yaml(adaptiveProtectionConfig)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Update with more aggressive settings
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-confidence-threshold=0.60 \
  --adaptive-protection-auto-deploy-impacted-baseline-threshold=0.70 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Update with more conservative settings
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-confidence-threshold=0.90 \
  --adaptive-protection-auto-deploy-impacted-baseline-threshold=0.90 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Auto-Deploy Rules

### How Auto-Deploy Works

1. ML detects anomalous traffic pattern
2. Confidence exceeds threshold
3. Rule automatically created with deny action
4. Security team notified
5. Rule remains active for configured duration

### View Auto-Deployed Rules

```bash
# List auto-deployed rules
gcloud compute security-policies rules list \
  --security-policy={{user.policy_name}} \
  --format="table(priority,expression,action,description)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" | grep "auto-deploy"
```

### Auto-Deploy Rule Lifecycle

| Phase | Duration | Action |
|-------|----------|--------|
| Creation | Immediate | Rule deployed with deny action |
| Active | 2 hours (default) | Traffic blocked |
| Review | After notification | Security team reviews |
| Extension | If attack continues | Rule extended |
| Expiration | Auto | Rule removed after cooldown |

### Configure Rule Duration

```bash
# Set auto-deploy rule TTL (in seconds)
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-rule-ttl=7200 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Manual Override

```bash
# Disable auto-deployment (use manual review only)
gcloud compute security-policies update {{user.policy_name}} \
  --no-adaptive-protection-auto-deploy-enabled \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Re-enable auto-deployment
gcloud compute security-policies update {{user.policy_name}} \
  --adaptive-protection-auto-deploy-enabled \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Review Auto-Deploy Events

```bash
# View adaptive protection events
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.adaptiveProtectionAutoDeploy' \
  --limit=100 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Alerting

### Create Alert Policy

```bash
# Create notification channel
gcloud alpha monitoring channels create \
  --display-name="Security Alerts" \
  --type=email \
  --channel-labels="email_address=security@example.com" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Get notification channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --format="value(name)" \
  --filter="displayName='Security Alerts'" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}")

# Create alert for adaptive protection events
gcloud alpha monitoring policies create \
  --notification-channels="$CHANNEL_ID" \
  --display-name="Cloud Armor Adaptive Protection Alert" \
  --condition-display-name="Adaptive Protection Triggered" \
  --condition-filter='metric.type="compute.googleapis.com/security_policy/adaptive_protection" resource.type="http_load_balancer"' \
  --condition-threshold-value=1 \
  --condition-threshold-comparison=COMPARISON_GT \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Cloud Armor Alerts

```bash
# Create log-based alert for adaptive protection
gcloud logging sinks create armor-alert-sink \
  --storage-destination="projects/{{env.CLOUDSDK_CORE_PROJECT}}/datasets/security_logs" \
  --log-filter='resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.adaptiveProtectionAutoDeploy'

# Alert on rule creation
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.method="GOOGLE_ARMOR_ADAPTIVE_PROTECTION_AUTO_DEPLOY_RULE_CREATED"' \
  --limit=10 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Alert Thresholds

| Alert Type | Trigger | Recommended Action |
|------------|---------|-------------------|
| `ADAPTIVE_PROTECTION_ENABLED` | Protection activated | Verify legitimate traffic |
| `AUTO_DEPLOY_RULE_CREATED` | New rule auto-deployed | Review rule details |
| `HIGH_CONFIDENCE_ATTACK` | Confidence > 0.95 | Immediate investigation |
| `AUTO_DEPLOY_RULE_EXPIRED` | Rule TTL reached | Assess if extension needed |

## Monitoring

### View Adaptive Protection Status

```bash
# Describe security policy with adaptive protection
gcloud compute security-policies describe {{user.policy_name}} \
  --format="yaml(adaptiveProtectionConfig)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Cloud Monitoring Metrics

| Metric | Description |
|--------|-------------|
| `compute.googleapis.com/security_policy/adaptive_protection` | Adaptive protection status |
| `compute.googleapis.com/security_policy/request_count` | Total request count |
| `compute.googleapis.com/security_policy/adaptive_protection_blocked_requests` | Requests blocked by adaptive protection |

### Dashboard Setup

```bash
# Create custom dashboard
gcloud monitoring dashboards create \
  --config-from-file=adaptive-protection-dashboard.json \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### adaptive-protection-dashboard.json

```json
{
  "displayName": "Cloud Armor Adaptive Protection",
  "gridLayout": {
    "widgets": [
      {
        "title": "Adaptive Protection Events",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": 'metric.type="compute.googleapis.com/security_policy/adaptive_protection"'
              }
            }
          }]
        }
      },
      {
        "title": "Blocked Requests by Adaptive Protection",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": 'metric.type="compute.googleapis.com/security_policy/adaptive_protection_blocked_requests"'
              }
            }
          }]
        }
      }
    ]
  }
}
```

### Query Adaptive Protection Logs

```bash
# View all adaptive protection events
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.adaptiveProtectionAutoDeploy' \
  --format="table(timestamp,jsonPayload.enforcedSecurityPolicy.adaptiveProtectionAutoDeploy)" \
  --limit=50 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# View auto-deploy rule creations
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.method="GOOGLE_ARMOR_ADAPTIVE_PROTECTION_AUTO_DEPLOY_RULE_CREATED"' \
  --limit=20 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Best Practices

1. **Enable Adaptive Protection**: Always enable for internet-facing applications
2. **Start with Auto-Deploy**: Use balanced thresholds initially
3. **Monitor for 2 Weeks**: Allow baseline learning before tuning
4. **Review Auto-Deployed Rules**: Check daily during active attacks
5. **Maintain Communication**: Set up alerts for immediate notification
6. **Document Exceptions**: Record allowlisted IPs to avoid accidental blocks
7. **Regular Review**: Monthly review of adaptive protection events
8. **Coordinate with Teams**: Ensure DevOps knows when rules auto-deploy

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Auto-deploy not working | Threshold too high | Lower confidence threshold |
| Too many false positives | Threshold too low | Raise thresholds |
| No baseline learning | Insufficient traffic | Wait 7-14 days |
| Alert not received | Notification misconfigured | Verify channel settings |

### Debug Commands

```bash
# Check adaptive protection status
gcloud compute security-policies describe {{user.policy_name}} \
  --format="json" | jq '.adaptiveProtectionConfig'

# View recent adaptive protection events
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.adaptiveProtectionAutoDeploy' \
  --limit=20 \
  --order=desc \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Test adaptive protection trigger
gcloud compute security-policies update {{user.policy_name}} \
  --enable-adaptive-protection \
  --adaptive-protection-auto-deploy-confidence-threshold=0.50 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Verify log sink
gcloud logging sinks describe armor-alert-sink \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Check ML Model Status

```bash
# View adaptive protection ML status
gcloud compute security-policies describe {{user.policy_name}} \
  --format="yaml(adaptiveProtectionConfig.layer7DdosDefenseConfig)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## See Also

- [Advanced WAF Rules](advanced-waf-rules.md)
- [Bot Management](bot-management.md)
- [Core Concepts](../core-concepts.md)
- [Monitoring](../monitoring.md)
- [Google Cloud Armor Adaptive Protection](https://cloud.google.com/armor/docs/adaptive-protection)
