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

## Attack Mitigation Self-Healing (自愈闭环)

> Adaptive protection auto-deploys rules, but **auto-deploy is not auto-hardening**. This section closes the loop: when adaptive protection triggers, the agent proposes a **permanent** security-policy hardening, previews it (dry-run), and waits for a **human review gate** before applying. All actions are idempotent and credential-masked (root `AGENTS.md` §0.1).

### Blast Radius First

Armor sits **in front of** the Load Balancer backend enforcement. A hardened rule can impact `gcp-gce-ops` (backend VMs/MIGs), `gcp-vpc-ops` (VPC firewall), and `gcp-cdn-ops` (origin cache fills). Compute the blast radius **before** any preview — see [`docs/cross-skill-blast-radius.md`](../../../docs/cross-skill-blast-radius.md) (T1/T2/T3 tiers).

### Self-Healing Flow

```
Adaptive trigger ──► 1. Detect auto-deploy event
       │
       ▼
  2. Classify error via docs/error-taxonomy.md (Recovery Action Vocabulary)
       │
       ▼
  3. DRY-RUN preview of proposed hardening (no mutation)
       │
       ▼
  4. Human review gate (T2/T3 = HALT until explicit confirm)
       │
       ▼
  5. Idempotent APPLY (converge to target state)
       │
       ▼
  6. Validate + monitor; auto-expired auto-deploy rule may be retired
```

### Step 1 — Detect Auto-Deploy Event

```bash
# List recent adaptive protection auto-deploy rule creations
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.method="GOOGLE_ARMOR_ADAPTIVE_PROTECTION_AUTO_DEPLOY_RULE_CREATED"' \
  --limit=20 --order=desc \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Step 2 — Classify (error-taxonomy)

Map the trigger to a recovery action from [`docs/error-taxonomy.md`](../../../docs/error-taxonomy.md):
- `PREVIEW` → emit dry-run, no apply.
- `RETRY` → re-read policy fingerprint, then preview.
- `HALT` → cross-skill impact (T3) or destructive; stop and request confirmation.

### Step 3 — DRY-RUN Preview (no mutation)

Propose a permanent rule mirroring the auto-deployed expression, but **do not apply**. Use `--format=json` and show the diff against the current policy fingerprint.

```bash
# Preview: show current rules + the proposed priority/expression WITHOUT creating it
gcloud compute security-policies rules list {{user.policy_name}} \
  --format="json" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" | jq '.[] | {priority, expression, action}'

# Proposed hardening (shown to human, NOT executed):
#   gcloud compute security-policies rules create <priority> \
#     --security-policy={{user.policy_name}} \
#     --expression="<mirrored auto-deploy expression>" \
#     --action="deny-403" --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

> **Idempotency:** The proposed priority is derived deterministically from the attack signature hash, so re-running the self-heal converges to the same rule (no duplicate creation).

### Step 4 — Human Review Gate

| Blast-radius tier | Gate |
|-------------------|------|
| T1 (single rule) | Dry-run log only; auto-approve after preview |
| T2 (policy-wide, e.g. enable auto-deploy) | **Human gate** — present preview, await confirm |
| T3 (cross-skill: fail-closed / delete) | **HALT** — explicit resource-identifier confirmation required |

Destructive or cross-skill actions are marked **HALT** and MUST NOT auto-apply.

### Step 5 — Idempotent Apply (after gate)

```bash
# Only after human confirmation (T2) or never for T3 without explicit assent
gcloud compute security-policies rules create {{user.rule_priority}} \
  --security-policy={{user.policy_name}} \
  --expression="<mirrored auto-deploy expression>" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Step 6 — Validate & Monitor

```bash
gcloud compute security-policies rules list {{user.policy_name}} \
  --format="json" | jq '.[] | select(.priority == {{user.rule_priority}})'
# Confirm no legitimate traffic blocked via monitoring metrics
# compute.googleapis.com/security_policy/adaptive_protection_blocked_requests
```

### Safety Constraints

- **Credential masking (§0.1):** Never log `GOOGLE_APPLICATION_CREDENTIALS` or SA key content; verify existence only.
- **No silent apply:** T2/T3 require human gate; auto-deploy rule retirement is the only unattended step (it is a no-op when already expired).
- **Rollback:** To revert, delete the hardened rule by its deterministic priority (idempotent).

## See Also

- [Advanced WAF Rules](advanced-waf-rules.md)
- [Bot Management](bot-management.md)
- [Core Concepts](../core-concepts.md)
- [Monitoring](../monitoring.md)
- [Google Cloud Armor Adaptive Protection](https://cloud.google.com/armor/docs/adaptive-protection)
