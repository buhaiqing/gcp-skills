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

> **Self-Healing Safety Contract (MANDATORY):** Every mutating action below is
> **dry-run first → human review gate → apply**. No silent mute/resolve. Mute/resolve
> are GCL `required` (see SKILL.md Quality Gate). Credentials are masked per
> AGENTS.md §0.1 — never print `GOOGLE_APPLICATION_CREDENTIALS` content or tokens.

### Self-Healing Runbook: Auto-mute Low-Severity Findings

The pseudo-code above is replaced by an **idempotent, gated `gcloud`** flow. It
mutes only via a **Mute Config** (scoped, reversible) — never per-finding
`MUTED` state writes, which are hard to audit and reverse.

**Variables (Structured I/O):**
- `{{env.CLOUDSDK_CORE_PROJECT}}` — never ask; HALT if unset.
- `{{user.org_id}}` — org number (ask once).
- `{{user.mute_config_id}}` — idempotent config name (ask once).
- `{{user.confirm_mute}}` — explicit `yes` gate before apply (ask once).

#### Step 1 — Pre-flight (no mutation)

```bash
# Verify auth + project without exposing credentials (existence only, §0.1)
test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists (masked)"
gcloud config get-value project
gcloud scc mute-configs list --organization="{{user.org_id}}" --format=json \
  | jq -r '.[].name' || true
```

#### Step 2 — DRY-RUN: preview the exact findings the mute config would cover

```bash
# Build a filter for low-severity, active findings (adjust category as needed)
MUTE_FILTER='state="ACTIVE" AND severity="LOW"'

# Preview matching findings — NO mutation, just a count + sample
gcloud scc findings list "organizations/{{user.org_id}}/sources/-" \
  --filter="$MUTE_FILTER" --format=json \
  | jq '{matched: length, sample: [.[0:5][].name]}'
echo "[DRY-RUN] Would create mute config '{{user.mute_config_id}}' covering the findings above."
```

#### Step 3 — HUMAN REVIEW GATE (HALT until explicit confirmation)

```bash
# Idempotent guard: skip if the mute config already exists
if gcloud scc mute-configs describe "{{user.mute_config_id}}" \
     --organization="{{user.org_id}}" --format='value(name)' 2>/dev/null; then
  echo "[GATE] Mute config already exists — idempotent skip (no re-apply)."
  exit 0
fi

# HALT: require explicit human confirmation before any mutating apply
if [ "{{user.confirm_mute}}" != "yes" ]; then
  echo "[HALT] confirm_mute != 'yes'. Aborting mute apply. Present DRY-RUN output for review."
  exit 1
fi
```

#### Step 4 — APPLY (only after gate passes)

```bash
# Create the mute config (scoped, reversible, idempotent via Step 3 guard)
gcloud scc mute-configs create "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" \
  --description="AIOps auto-mute: low-severity active findings (self-healing, reviewed)" \
  --filter="$MUTE_FILTER" \
  --format=json
```

#### Step 5 — VALIDATE (confirm coverage, no credential leak)

```bash
gcloud scc mute-configs describe "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" --format=json \
  | jq '{name, filter, description, createTime}'
```

#### Step 6 — RECOVER (reversible — delete the mute config to un-mute)

```bash
# Deleting a mute config is destructive → GCL required, explicit confirm
# gcloud scc mute-configs delete "{{user.mute_config_id}}" --organization="{{user.org_id}}"
echo "[RECOVER] To un-mute, run the delete above with explicit confirmation (GCL required)."
```

### Self-Healing Runbook: Auto-close Stale Findings

Stale auto-close is **more destructive** (state `INACTIVE` hides findings from
dashboards). Treat as **HALT + GCL required**; prefer a time-bounded mute config
over per-finding state writes.

```bash
# DRY-RUN: preview stale ACTIVE findings older than 30 days
CUTOFF=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
         || date -u -v-30d +%Y-%m-%dT%H:%M:%SZ)
STALE_FILTER="state=\"ACTIVE\" AND eventTime < \"$CUTOFF\""

gcloud scc findings list "organizations/{{user.org_id}}/sources/-" \
  --filter="$STALE_FILTER" --format=json \
  | jq '{matched: length, sample: [.[0:5][].name]}'
echo "[DRY-RUN] Stale auto-close is HALT — requires human review + GCL before any apply."
```

> **Never** loop `update-finding` with `state=INACTIVE` in an unattended agent.
> If a stale-close is approved, apply via a reviewed mute config (reversible) and
> record the GCL trace under `./audit-results/gcl-trace-*.json`.

## Blast Radius: Impact of Muting / Silencing Findings

Muting or auto-closing SCC findings is **not local** — a false-positive silence
can suppress real signals across downstream consumers. Before any self-healing
mute, assess the blast radius:

| Downstream Consumer | What Breaks If a Real Finding Is Muted | Reversibility |
|---------------------|----------------------------------------|---------------|
| **Pub/Sub notification configs** | Real HIGH/CRITICAL findings stop reaching SIEM/SOAR webhooks → no incident ticket | Recover by deleting mute config (Step 6) |
| **BigQuery continuous export** | Muted findings are still exported, but dashboards filtering on `mute!=MUTED` hide them → false "all clear" | Re-query with `mute` column; partial |
| **Cloud Monitoring alert policies** | Velocity/severity alerts keyed on ACTIVE count drop → silent degradation | Re-enable via un-mute; partial |
| **Security Health Analytics posture** | Posture score may improve artificially while risk persists | Re-score after un-mute |
| **Cross-skill chains** (`gcp-iam-ops`, `gcp-pubsub-ops`, `gcp-bigquery-ops`) | Dependent automations assume findings flow; a mute can stall their triggers | Per-skill recovery |

**Blast-radius guardrails (apply before mute):**
1. **Never mute above `LOW`** in an unattended self-healing flow — MEDIUM+ requires human review.
2. **Scope the mute config narrowly** (specific `category` + `resourceName` where possible) instead of a blanket `severity="LOW"`.
3. **Keep a time-to-live**: review muted findings weekly (see Best Practices) and expire stale mute configs.
4. **Cross-skill note**: a mute in SCC can stall triggers owned by other skills — coordinate via their runbooks, do not assume isolation.

> See [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) for the
> repo-wide blast-radius methodology and [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)
> for SCC-specific error codes and HALT/retry classification.

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
- [Error Taxonomy (repo-wide)](../../../docs/error-taxonomy.md) — SCC-specific error codes, HALT vs retry
- [Cross-Skill Blast Radius (repo-wide)](../../../docs/cross-skill-blast-radius.md) — impact propagation across skills
- [SKILL.md AIOps 自愈指引](../../SKILL.md) — entry-point self-healing guidance and GCL gate
