# GCL Prompt Templates — Filestore

## Generator Template

Hard rules:

1. Safety gates on all destructive ops (delete instance, delete backup, restore from backup)
2. Follow per-op sub-rules in [references/rubric.md](rubric.md)
3. Use env vars for credentials; NEVER output credential values
4. Use `--format=json` for gcloud filestore commands
5. Verify instance name unique per zone/region before create
6. Verify instance exists before delete
7. Suggest backup before destructive operations
8. Check capacity limits per tier before create/update
9. Check backup rate limit (1 per 10 minutes) before create
10. Use correct zone/region flag: `--zone=ZONE` for zonal, `--region=REGION` for regional/enterprise
11. Delegate IAM ops to gcp-iam-ops, VPC to gcp-vpc-ops, KMS to gcp-kms-ops

## Critic Template

CRITICAL: Critic MUST NOT see the user's original request.

```json
{
  "dimensions": {
    "Correctness": "PASS|FAIL",
    "Safety": "PASS|FAIL|0",
    "Idempotency": "PASS|FAIL",
    "Traceability": "PASS|FAIL",
    "Spec Compliance": "PASS|FAIL"
  },
  "extensions": {
    "Instance Name Uniqueness": "PASS|FAIL|N/A",
    "Capacity Validation": "PASS|FAIL|N/A",
    "Network Config Validation": "PASS|FAIL|N/A",
    "Backup Rate Limit": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: `--quiet.*delete`, `instances.*delete`, `backups.*delete`, `restore`, `scale.*capacity`, `--force`

## Orchestrator

Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=3 (recommended tier).

## Hallucination Detector (H) Template

Added in GCL v1.5.0. Pre-execution structural validity check.

Check for:

1. **Invalid tier names**: Must be BASIC_HDD, BASIC_SSD, HIGH_SCALE_SSD, ZONAL, REGIONAL, ENTERPRISE
2. **Invalid capacity**: Check against tier limits
3. **Invalid zone/region**: Verify against `gcloud filestore locations list`
4. **Invalid network**: Verify VPC network exists
5. **Command syntax errors**: Verify gcloud flags are valid

```markdown
## Hallucination Check

Before executing the generated commands, verify:

1. Tier name is valid: {{user.tier}} ∈ {BASIC_HDD, BASIC_SSD, ZONAL, REGIONAL, ENTERPRISE}
2. Capacity is within tier limits:
   - BASIC_HDD: 1 TiB – 63.9 TiB
   - BASIC_SSD: 2.5 TiB – 63.9 TiB
   - ZONAL: 1 TiB – 9.75 TiB or 10 TiB – 100 TiB
   - REGIONAL: 100 GiB – 9.75 TiB or 10 TiB – 100 TiB
   - ENTERPRISE: 1 TiB – 10 TiB
3. Zone/region is valid: `gcloud filestore zones list`
4. Network exists: `gcloud compute networks list`
5. Command syntax: All required flags present

If any check fails, HALT and report hallucination.
```

## Factual Accuracy Rule

The Critic MUST verify that generated content is complete, up-to-date, and truthful. If any stale, inaccurate, or unverifiable information is found, it MUST be corrected immediately. If the Critic cannot confidently verify the accuracy, it MUST HALT and escalate to human review rather than proceed with uncertain content.

## Example Generator Output

### PASS: Create Instance with Validation

```
[DIAG] Creating Filestore instance: my-instance
[DIAG] Tier: ZONAL
[DIAG] Capacity: 2 TiB (valid for ZONAL: 1-9.75 TiB)
[DIAG] Zone: us-central1-a
[DIAG] Network: default

Verifying instance does not exist...
Instance does not exist — proceeding with creation.

Executing:
gcloud filestore instances create my-instance \
  --zone=us-central1-a \
  --tier=ZONAL \
  --file-share=name=vol1,capacity=2TiB \
  --network=name=default \
  --format=json

[RESULT] Created instance: my-instance
[RESULT] IP Address: 10.0.0.5
[RESULT] Mount path: 10.0.0.5:/vol1
```

### SAFETY_FAIL: Delete Instance without Confirmation

```
gcloud filestore instances delete my-instance --zone=us-central1-a --quiet
```

**Critic Verdict: SAFETY_FAIL — ABORT**

Reason: `--quiet` flag bypasses confirmation, no backup suggested.

## Trace Schema

Every GCL run MUST persist a JSON trace to `./audit-results/gcl-trace-*.json` (gitignored).

```json
{
  "skill": "gcp-filestore-ops",
  "operation": "create_instance",
  "timestamp": "2026-06-13T10:00:00Z",
  "generator_output": "...",
  "critic_output": "...",
  "hallucination_check": {...},
  "verdict": "PASS",
  "issues": [],
  "trace_file": "./audit-results/gcl-trace-filestore-20260613-100000.json"
}
```
