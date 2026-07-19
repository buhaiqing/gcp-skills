# AIOps Self-Healing Anchors — Google Cloud Functions

> Anomaly detection + self-healing runbook for Cloud Functions (gen1/gen2). Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Cold-start timeout / init failure | High | Auto (with gate) |
| FM-2 | Concurrency limit exceeded (429 / throttling) | Medium | Auto (with gate) |
| FM-3 | Deploy/rollback failure (broken revision) | High | Auto (with gate) |

---

## FM-1: Cold-Start Timeout / Init Failure

### Detection

```bash
# Function status and last deploy error
gcloud functions describe "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{name, state, status: .status, updateTime}'

# Init / timeout errors in logs
gcloud functions logs read "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=50 | grep -iE "timeout|init|crash|OOM" || true

# Execution time metric
gcloud monitoring time-series list \
  --filter='metric.type="cloudfunctions.googleapis.com/function/execution_times" AND resource.labels.function_name="{{user.function_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.doubleValue'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Increase timeout / memory (gen2) | `--dry-run` | Yes | **Human review** — cost impact |
| 2 | Set `min-instances > 0` to avoid cold start | `--dry-run` | Yes | **Human review** — idle cost |

```bash
# DRY-RUN: preview config change
gcloud functions deploy "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --trigger-http \
  --timeout="{{user.new_timeout}}" --memory="{{user.new_memory}}" \
  --min-instances="{{user.min_instances}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** if init failure is a code bug — redeploy requires a fixed build; do not loop redeploys.

### Blast Radius

- **Upstream**: `gcp-secretmanager-ops` (secret mount at init); `gcp-vpc-ops` (VPC connector init delay).
- **Downstream**: `gcp-lb-ops` / `gcp-cloudrun-ops` (HTTP trigger front-end); Eventarc/PubSub triggers (event loss if failing).

---

## FM-2: Concurrency Limit Exceeded

### Detection

```bash
# Active instances vs concurrency
gcloud monitoring time-series list \
  --filter='metric.type="cloudfunctions.googleapis.com/function/active_instances" AND resource.labels.function_name="{{user.function_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.int64Value'

# Throttled invocations
gcloud monitoring time-series list \
  --filter='metric.type="cloudfunctions.googleapis.com/function/execution_count" AND metric.labels.result="throttled"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.int64Value'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Raise `max-instances` (quota permitting) | `--dry-run` | Yes | **Human review** — quota/cost |
| 2 | Raise per-instance concurrency | `--dry-run` | Yes | **Human review** |

```bash
# DRY-RUN: preview concurrency scaling
gcloud functions deploy "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --trigger-http \
  --max-instances="{{user.max_instances}}" --concurrency="{{user.concurrency}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** if max-instances would exceed project quota or budget guardrail — escalate.

### Blast Radius

- **Upstream**: `gcp-secretmanager-ops` (secret read at scale); `gcp-vpc-ops` (connector IP exhaustion).
- **Downstream**: callers (429 retry); `gcp-billing-ops` (cost spike).

---

## FM-3: Deploy / Rollback Failure (Broken Revision)

### Detection

```bash
gcloud functions describe "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{state, status: .status, buildConfig: .buildConfig, serviceConfig: .serviceConfig}'

# Recent deploy failures
gcloud functions logs read "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=30 \
  | grep -iE "deploy|build|FAILED" || true
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Roll back to last known-good revision (gen2) | `--dry-run` | No (state change) | **Human review** |
| 2 | If no good revision, disable traffic (HALT) | `--dry-run` | Yes | **HALT** — service outage |

```bash
# DRY-RUN: preview rollback to previous revision
gcloud functions deploy "{{user.function_name}}" --gen2 \
  --region="{{user.region}}" --trigger-http \
  --source="gs://{{env.CLOUDSDK_CORE_PROJECT}}_cloudbuild/source/{{user.last_good_rev}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Prefer rollback over disable. **HALT** on any delete of a function serving production traffic.

### Blast Radius

- **Upstream**: `gcp-cloudbuild-ops` (build pipeline); `gcp-secretmanager-ops` (secret ref in build).
- **Downstream**: `gcp-lb-ops` / `gcp-cloudrun-ops` (front-end); event triggers (Eventarc/PubSub).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-secretmanager-ops](../gcp-secretmanager-ops/SKILL.md) · [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) · [gcp-lb-ops](../gcp-lb-ops/SKILL.md) · [gcp-cloudbuild-ops](../gcp-cloudbuild-ops/SKILL.md)
