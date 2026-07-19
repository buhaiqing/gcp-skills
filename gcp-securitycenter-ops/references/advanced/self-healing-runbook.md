# SCC Self-Healing Runbook — AIOps Auto-Remediation

> **Purpose:** Single mainlined entry point for Security Command Center (SCC) AIOps self-healing. Detects security-finding anomalies and applies *gated, idempotent, reversible* remediation. The low-severity auto-mute flow lives here as the canonical implementation; the older fragment in [aiops-scc-anomaly.md](aiops-scc-anomaly.md#self-healing-runbook-auto-mute-low-severity-findings) is preserved for reference but this runbook is authoritative.
> **Classification:** GCL `required` (every mutating step is destructive / posture-impacting).
> **Error taxonomy:** [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) — recovery actions (`HALT`/`RETRY`/`REMEDIATE`/`ESCALATE`) and idempotency flags used below.

---

## 1. 触发条件 (Triggers)

| Trigger | Signal | Severity Floor | Auto-action class |
|---------|--------|----------------|-------------------|
| **High-severity finding surge** | Finding velocity for `HIGH`/`CRITICAL` exceeds 3× rolling 1h baseline | `HIGH` | `HALT` + `ESCALATE` (never auto-mute) |
| **Muted-finding drift** | A mute config covers findings that later turn `HIGH`/`CRITICAL`, or a stale mute covers >30d-old findings still `ACTIVE` | `LOW`→review | `REMEDIATE` via reviewed mute config only |
| **Misconfigured notification** | Pub/Sub notification config missing/inactive, or topic ACL blocks SCC publish → silent finding loss | any | `HALT` (notification fix is billing/alerting mutation) |
| **Resource-value over-ride drift** | A resource value config down-plays severity for a now-critical asset | `MEDIUM+` | `HALT` + human review |

> Blast-radius of any mute/notification change is **cross-skill** — a silence in SCC can stall triggers owned by `gcp-iam-ops`, `gcp-pubsub-ops`, `gcp-bigquery-ops`. See [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md). Never assume isolation.

---

## 2. 检测 (Detection)

All detection is **read-only** (`gcloud scc ... list/describe`). No mutation in this phase.

### 2.1 High-severity surge

```bash
# Count HIGH/CRITICAL active findings in the last hour vs previous hour
PARENT="organizations/{{user.org_id}}/sources/-"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
HOUR_AGO=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)

RECENT=$(gcloud scc findings list "$PARENT" \
  --filter="state=\"ACTIVE\" AND severity=HIGH OR severity=CRITICAL AND eventTime>=\"$HOUR_AGO\"" \
  --format=json | jq 'length')
PREV=$(gcloud scc findings list "$PARENT" \
  --filter="state=\"ACTIVE\" AND severity=HIGH OR severity=CRITICAL AND eventTime<\"$HOUR_AGO\" AND eventTime>=\"$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-2H +%Y-%m-%dT%H:%M:%SZ)\"" \
  --format=json | jq 'length')

echo "[DETECT] recent=$RECENT prev=$PREV"
# Surge if PREV>0 and RECENT > PREV*3 → HALT + ESCALATE
```

### 2.2 Muted-finding drift

```bash
# Findings currently muted but carrying HIGH/CRITICAL severity (mute drift)
gcloud scc findings list "$PARENT" \
  --filter="state=\"ACTIVE\" AND mute=\"MUTED\" AND (severity=HIGH OR severity=CRITICAL)" \
  --format=json | jq '{drifted: length, sample: [.[0:5][].name]}'

# Stale mute configs covering >30d-old ACTIVE findings
CUTOFF=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30d +%Y-%m-%dT%H:%M:%SZ)
gcloud scc findings list "$PARENT" \
  --filter="state=\"ACTIVE\" AND eventTime<\"$CUTOFF\" AND mute=\"MUTED\"" \
  --format=json | jq '{stale_muted: length}'
```

### 2.3 Misconfigured notification

```bash
# Is the notification config present and active?
gcloud scc notifications list --organization="{{user.org_id}}" --format=json \
  | jq '.[] | {name, serviceAccount, pubsubTopic}'

# Can SCC's service account publish to the topic? (permission drift → PERMISSION_DENIED)
TOPIC=$(gcloud scc notifications describe "{{user.notif_config_id}}" \
  --organization="{{user.org_id}}" --format='value(pubsubTopic)')
gcloud pubsub topics get-iam-policy "${TOPIC#*topics/}" --format=json \
  | jq '.bindings[]? | select(.role=="roles/pubsub.publisher")'
```

> Auth/setup checks use existence-only verification per AGENTS.md §0.1 — never print `GOOGLE_APPLICATION_CREDENTIALS` content:
> `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists (masked)"`

---

## 3. 自愈动作 (Self-Healing Actions)

Every action follows **DRY-RUN → 人工复核门禁 → APPLY → VALIDATE → RECOVER**. Mute/resolve are realized only through **Mute Configs** (scoped, reversible, auditable) — never per-finding `MUTED`/`INACTIVE` state writes, which are hard to reverse and audit.

### 3.1 Auto-mute low-severity findings (canonical flow)

**Recovery action:** `REMEDIATE` (idempotent_safe = true). **Gate:** `{{user.confirm_mute}} == "yes"`, else `HALT`.

The end-to-end auto-mute implementation (Pre-flight → DRY-RUN → 人工复核门禁 → APPLY → VALIDATE → RECOVER, with idempotency guard) is the **authoritative** copy maintained in the legacy fragment:

> 详见 [aiops-scc-anomaly.md §Self-Healing Runbook: Auto-mute Low-Severity Findings](aiops-scc-anomaly.md#self-healing-runbook-auto-mute-low-severity-findings)

This runbook does **not** re-narrate those steps — it is the orchestration entry point. Runbook-specific additions layered on top of that flow:

- **GCL wrapper:** every `mute-configs create` must pass through `gcl_runner_enhanced.py` (§5) which enforces the DRY-RUN evidence + human gate before APPLY.
- **Idempotency:** the fragment's Step 3 existence guard makes repeated runs a no-op if the config exists.
- **Reversibility:** delete the config (fragment Step 6) — destructive, GCL required.
- **Blast-radius guard:** never mute above `LOW` unattended; scope `category`+`resourceName` where possible; keep a weekly TTL review.

### 3.2 Auto-close stale findings

**Recovery action:** `HALT` (prefer time-bounded mute config over per-finding state writes).

```bash
CUTOFF=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30d +%Y-%m-%dT%H:%M:%SZ)
STALE_FILTER="state=\"ACTIVE\" AND eventTime < \"$CUTOFF\""
gcloud scc findings list "organizations/{{user.org_id}}/sources/-" \
  --filter="$STALE_FILTER" --format=json \
  | jq '{matched: length, sample: [.[0:5][].name]}'
echo "[DRY-RUN] Stale auto-close is HALT — requires human review + GCL before any apply."
```

> Never loop `update-finding` with `state=INACTIVE` in an unattended agent. If approved, apply via a reviewed mute config (reversible) and record the GCL trace under `./audit-results/gcl-trace-*.json`.

### 3.3 Fix misconfigured notification

**Recovery action:** `HALT` (notification/topic mutation is alerting-impacting). Diagnose drift, then require human review before re-creating the config or re-granting `roles/pubsub.publisher` to SCC's service account.

```bash
# Diagnose: which part is broken?
gcloud scc notifications describe "{{user.notif_config_id}}" --organization="{{user.org_id}}" --format=json \
  | jq '{name, pubsubTopic, serviceAccount, streamingConfig}'
# If topic ACL missing SCC publisher → PERMISSION_DENIED (Permission dim, idempotent_safe=true REMEDIATE)
# If config deleted → NOT_FOUND (Resource State dim, HALT: recreate needs human ack)
```

---

## 4. 错误分类映射 (Error-Taxonomy Mapping)

| Self-healing failure | error-taxonomy code | Dimension | Recovery | idempotent_safe |
|----------------------|---------------------|-----------|----------|:----------------:|
| `gcloud scc` returns 403 on mute-config create | `PERMISSION_DENIED` | Permission | `REMEDIATE` (grant `roles/securitycenter.muteConfigsEditor`) | true |
| SA key missing/expired | `AUTH_FAILED` | Authentication | `REMEDIATE` (fix `GOOGLE_APPLICATION_CREDENTIALS`) | true |
| Notification topic ACL blocks publish | `PERMISSION_DENIED` | Permission | `REMEDIATE` (grant publisher role) | true |
| Notification config not found | `NOT_FOUND` | Resource State | `HALT` (recreate needs human ack) | true |
| `gcloud scc` API timeout / 503 | `UNAVAILABLE` / `TIMEOUT` | Network | `RETRY` (exponential backoff) | true |
| Rate-limited on bulk finding list | `RATE_LIMITED` | Rate Limit | `RETRY` (reduce concurrency) | true |
| etag conflict on config update | `ABORTED` | Dependency | `RETRY` (re-fetch etag) | true |
| Invalid mute filter expression | `INVALID_ARGUMENT` | Configuration | `HALT` (fix filter per API) | true |

Full vocabulary and dimension index: [docs/error-taxonomy.md](../../../docs/error-taxonomy.md).

---

## 5. GCL 连接段 (GCL Integration)

Every mutating self-healing step must pass through the Generator-Critic-Loop before apply. SCC is GCL `required` with `max_iter: 2` (see SKILL.md Quality Gate).

```bash
# Run the enhanced GCL gate over a self-healing op before applying it.
# Pass the exact gcloud command; the runner enforces dry-run evidence + human gate.
python3 gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py \
  --skill gcp-securitycenter-ops \
  --op CreateMuteConfig \
  --command 'gcloud scc mute-configs create "{{user.mute_config_id}}" --organization="{{user.org_id}}" --filter="state=\"ACTIVE\" AND severity=\"LOW\"" --format=json'

# After the run, aggregate the produced trace into the closed-loop quality report:
python3 gcp-gcl-runner-ops/trace_feedback.py \
  --trace-dir ./audit-results \
  --report-path ./audit-results/scc-self-healing-report.md
```

- **`gcl_runner_enhanced.py`** — adversarial Generator-Critic gate; enforces that dry-run output and the human-review gate exist before any mutating `APPLY`.
- **`trace_feedback.py`** — closes the loop: scans `./audit-results/gcl-trace-*.json` and aggregates self-healing failure patterns back into skill improvement. Traces from §3 feed cross-skill analytics in [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md).

Persist every GCL trace under `./audit-results/gcl-trace-*.json` (sanitized params, responses, validation evidence, reviewer decision).

---

## 6. Blast Radius & Guardrails

Muting/silencing SCC findings is **not local** — a false-positive silence suppresses real signals across downstream consumers.

| Downstream Consumer | What Breaks If a Real Finding Is Muted | Reversibility |
|---------------------|----------------------------------------|---------------|
| Pub/Sub notification configs | Real HIGH/CRITICAL findings stop reaching SIEM/SOAR → no ticket | Delete mute config (§3.1 Step 6) |
| BigQuery continuous export | Muted findings still exported, but `mute!=MUTED` dashboards hide them → false "all clear" | Re-query with `mute` column; partial |
| Cloud Monitoring alert policies | Velocity/severity alerts keyed on ACTIVE count drop → silent degradation | Un-mute; partial |
| Security Health Analytics posture | Posture score may improve artificially while risk persists | Re-score after un-mute |
| Cross-skill chains (`gcp-iam-ops`, `gcp-pubsub-ops`, `gcp-bigquery-ops`) | Dependent automations assume findings flow; a mute can stall their triggers | Per-skill recovery |

**Guardrails (apply before any mute):**
1. Never mute above `LOW` unattended — MEDIUM+ requires human review.
2. Scope the mute config narrowly (`category` + `resourceName`) instead of blanket `severity="LOW"`.
3. Keep a TTL: review muted findings weekly and expire stale mute configs.
4. Cross-skill coordination: a mute can stall other skills' triggers — coordinate via their runbooks, do not assume isolation.

> 跨域 blast-radius 细节与降级顺序见 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md).

---

## 7. See Also

- [SCC Auto-mute fragment (legacy)](aiops-scc-anomaly.md#self-healing-runbook-auto-mute-low-severity-findings) — preserved reference; this runbook is authoritative.
- [SCC SKILL.md AIOps 自愈指引](../../SKILL.md) — entry-point guidance and GCL gate.
- [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) — recovery vocabulary and dimension index.
- [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — repo-wide blast-radius methodology.
- [gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py) — GCL gate runner.
- [gcp-gcl-runner-ops/trace_feedback.py](../../../gcp-gcl-runner-ops/trace_feedback.py) — closed-loop trace aggregation.
