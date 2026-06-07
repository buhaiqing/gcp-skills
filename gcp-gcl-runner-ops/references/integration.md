# Integration — gcp-gcl-runner-ops

> **Purpose:** Cross-skill integration patterns and Cloud Audit Logs cross-check.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Cross-Skill Integration

Other skills delegate GCL execution to `gcp-gcl-runner-ops` via:

```markdown
## Delegation Rules
| 能力 | 委托目标 | 说明 |
|------|----------|------|
| GCL 质量门禁 | `gcp-gcl-runner-ops` | 执行前运行 GCL 验证 |
```

## Cloud Audit Logs Cross-Check

For each `gcl-trace-*.json`, an independent Cloud Audit Logs query verifies the operation actually happened:

```bash
gcloud logging read \
  "protoPayload.methodName={op} AND protoPayload.resourceName=projects/_/..." \
  --project={{env.CLOUDSDK_CORE_PROJECT}} \
  --format="json"
```

### Detection Types

| Finding | Meaning |
|---------|---------|
| `PHANTOM_PASS` | Critic said PASS but no audit log entry found (hallucinated execution) |
| `PHANTOM_FAIL` | Critic said FAIL but audit log shows the op completed successfully |
| `RESOURCE_MISMATCH` | Resource in command doesn't match audit log |
| `TIMING_ANOMALY` | Operation timestamp outside expected window |

### Script

```bash
python3 gcp-gcl-runner-ops/scripts/gcl_auditlog_crosscheck.py \
  --trace-file ./audit-results/gcl-trace-20260607-*.json \
  --project {{env.CLOUDSDK_CORE_PROJECT}}
```

## Cloud Monitoring Alarms

GCL pass-rate metrics can be pushed to Cloud Monitoring via `gcl_passrate_reporter.py`:

```bash
python3 gcp-gcl-runner-ops/scripts/gcl_passrate_reporter.py \
  --audit-dir ./audit-results/ \
  --project {{env.CLOUDSDK_CORE_PROJECT}}
```

This creates custom metrics under the `custom.googleapis.com/gcl/` namespace:

| Metric | Description |
|--------|-------------|
| `gcl/safety_fail_rate` | Rate of SAFETY_FAIL verdicts |
| `gcl/correctness_drop` | Correctness score < 0.5 rate |
| `gcl/pass_rate` | Overall GCL pass rate per skill |