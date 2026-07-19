# GCL Runner Scripts

This directory contains the implementation of the Generator-Critic-Loop (GCL) adversarial quality gate, defined in `AGENTS.md §11`.

## Files

| File | Purpose | Status |
|------|---------|--------|
| `gcl_runner.py` | Standalone Python 3.10+ CLI runner. Zero external deps. | ✅ Phase 2 |
| `gcl_runner_test.py` | Pure-stdlib unittest suite. | ✅ Phase 2 |
| `gcl_auditlog_crosscheck.py` | Phase 3-C cross-checker: verifies GCL traces against Cloud Audit Logs. | ✅ Phase 3 |
| `gcl_auditlog_crosscheck_test.py` | Pure-stdlib unittest suite for cross-check. | ✅ Phase 3 |
| `gcl_passrate_reporter.py` | Phase 4 pass-rate reporter: aggregates GCL traces, pushes to Cloud Monitoring. | ✅ Phase 4 |
| `gcl_monitoring_alarm_setup.py` | Phase 3-B + Phase 4 alarm setup: idempotent Cloud Monitoring alert policy creator. | ✅ Phase 4 |
| `README.md` | This file. | — |

## Quick Start

### 1. Pass-Through (real gcloud command)

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
export CLOUDSDK_CORE_PROJECT=my-project

python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet'
echo "exit: $?"  # 0 = PASS, 1 = MAX_ITER, 2 = SAFETY_FAIL
```

### 2. Dry-Run (Critic-Only Regression)

```bash
python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a' \
  --user-request "delete my-instance" \
  --dry-run
```

### 3. Custom Rubric Path

```bash
python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a' \
  --rubric /path/to/custom-rubric.md \
  --output-dir /custom/audit-dir
```

## Testing

The test suite lives under `gcp-gcl-runner-ops/tests/` (not in `scripts/`). Run it from the repo root with pytest:

```bash
python3 -m pytest gcp-gcl-runner-ops/tests/ -q
```

Or from within the skill directory:

```bash
cd gcp-gcl-runner-ops && python3 -m pytest
```

## Design Decisions

| Decision | Why |
|----------|-----|
| **Pure stdlib** | Zero external dependencies, works everywhere |
| **Mechanical Critic (not LLM)** | Deterministic, CI-friendly, free |
| **Subprocess for Generator (not SDK)** | Matches `gcloud` CLI as primary path |
| **Trace persisted as JSON** | `jq`-friendly; downstream tools can ingest |
| **Regex list parsed from rubric** | Adding a new skill = adding a new rubric; no code change |