# Enhanced GCL Runner (EGR) — Operational Handbook

> **Version:** 2.0.0 (Level 3)
> **Last Updated:** 2026-07-18

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [CLI Reference](#cli-reference)
3. [Exit Codes](#exit-codes)
4. [Output Format](#output-format)
5. [Example Workflows](#example-workflows)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Usage

```bash
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet'
```

### With BigQuery Upload

```bash
export CLOUDSDK_CORE_PROJECT=my-project
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
    --trace-to-bq
```

### Dry Run (Critic Only)

```bash
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
    --dry-run
```

---

## CLI Reference

### Required Arguments

| Flag | Description |
|------|-------------|
| `--skill` | Target skill name (e.g., `gcp-gce-ops`, `gcp-gcs-ops`) |
| `--op` | Operation name (e.g., `DeleteInstance`, `CreateBucket`) |
| `--command` | Full CLI command to execute (quote if contains spaces) |

### Optional Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--user-request` | - | Original natural-language user request for context |
| `--max-iter` | `2` | Maximum GCL iterations before giving up |
| `--rubric` | - | Custom rubric YAML file path |
| `--output-dir` | `audit-results/` | Directory for trace output files |
| `--dry-run` | `false` | Skip subprocess execution, run Critic only |
| `--trace-to-bq` | `false` | Enable BigQuery trace upload |
| `--degrade-threshold` | `3` | Consecutive failures before human degradation |
| `--environment` | `production` | Environment: `production`, `staging`, `development` |
| `--trace-only` | `false` | Async mode, don't wait for result |

---

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | PASS | GCL execution succeeded |
| `1` | MAX_ITER | Reached max iterations without consensus |
| `2` | SAFETY_FAIL | Permission denied or safety threshold violated |
| `3` | USAGE_ERROR | Invalid arguments or inline secrets detected |
| `4` | RUBRIC_ERROR | Rubric file not found or invalid |
| `5` | DEGRADED | Consecutive failures triggered human degradation |

---

## Output Format

### JSON Trace Structure

```json
{
  "trace_id": "gcl-trace-20260718-143052-abc123",
  "timestamp": "2026-07-18T14:30:52.123456+00:00",
  "skill": "gcp-gce-ops",
  "op": "DeleteInstance",
  "result": "PASS",
  "latency_ms": 1234,
  "autonomy_ratio": 0.85,
  "safety_score": 1.0,
  "environment": "production",
  "iterations": [
    {
      "iteration": 1,
      "generator_output": "gcloud compute instances delete...",
      "critic_output": "Approved",
      "decision": "EXECUTE",
      "exit_code": 0
    }
  ],
  "autonomy_decisions": [
    {
      "iteration": 1,
      "decision": "EXECUTE",
      "reason": "safety_score >= threshold"
    }
  ],
  "error_type": null,
  "pre_state": {
    "timestamp": "2026-07-18T14:30:51.000000+00:00",
    "command_hash": "a1b2c3d4",
    "working_dir": "/path/to/project",
    "git_branch": "main",
    "gcp_project": "my-project"
  },
  "post_state": {
    "timestamp": "2026-07-18T14:30:53.000000+00:00"
  },
  "retry_count": 0,
  "retry_delays": []
}
```

### Output Files

Traces are saved to:
- **Local**: `{output-dir}/gcl-trace-{trace_id}.json`
- **BigQuery**: `gcp_skills_gcl_audit.gcl_traces` table (if `--trace-to-bq` enabled)

---

## Example Workflows

### Workflow 1: Basic GCL Execution

```bash
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete old-vm --zone=us-central1-a --quiet' \
    --user-request "Delete the old VM as it's no longer needed"
```

### Workflow 2: With BigQuery + Cloud Logging

```bash
# Set GCP project
export CLOUDSDK_CORE_PROJECT=my-production-project

# Execute with full observability
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gcs-ops \
    --op SetBucketLifecycle \
    --command 'gsutil lifecycle set lifecycle-config.json gs://my-bucket' \
    --trace-to-bq \
    --environment production
```

### Workflow 3: Dry Run with Custom Rubric

```bash
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-iam-ops \
    --op AddIAMMember \
    --command 'gcloud projects add-iam-policy-binding my-project --member=user:new-user@company.com --role=roles/viewer' \
    --dry-run \
    --rubric ./custom-rubric.yaml
```

### Workflow 4: Staging Environment with Degradation

```bash
python3 scripts/gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op CreateInstance \
    --command 'gcloud compute instances create new-vm --zone=us-east1-b' \
    --environment staging \
    --degrade-threshold 5
```

---

## Troubleshooting

### Error: "Permission denied" (Exit code 2)

**Cause:** The command was blocked by the Critic due to safety threshold.

**Solution:**
- Check if the GCP service account has required permissions
- Review the rubric's safety rules for the operation
- Use `--dry-run` to test without execution

### Error: "Rubric file not found" (Exit code 4)

**Cause:** Custom rubric file doesn't exist or path is incorrect.

**Solution:**
```bash
# Verify rubric exists
ls -la ./my-rubric.yaml

# Use absolute path
python3 scripts/gcl_runner_enhanced.py \
    --rubric /absolute/path/to/my-rubric.yaml \
    ...
```

### Error: "Command contains inline secrets"

**Cause:** Password/API key detected in command string.

**Solution:**
- Use environment variables instead of inline secrets
- Use `--dry-run` to test without actual execution

### BigQuery Upload Fails Silently

**Cause:** Missing credentials or wrong project.

**Solution:**
```bash
# Verify credentials
gcloud auth list

# Verify project
gcloud config get-value project

# Set explicitly
export CLOUDSDK_CORE_PROJECT=my-project
```

### High Latency or Timeouts

**Cause:** Network issues or slow GCP API response.

**Solution:** The EGR has built-in retry with exponential backoff:
- Base delay: 1 second
- Max delay: 60 seconds
- Max retries: 3

For persistent issues, check GCP status at https://status.cloud.google.com/

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [LOGGING.md](LOGGING.md) - Structured logging guide
- [LOG_METRICS.md](LOG_METRICS.md) - Cloud Monitoring metrics
