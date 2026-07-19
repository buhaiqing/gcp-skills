# GCL Runner Scripts

> Generator-Critic-Loop (GCL) adversarial quality gate — defined in `AGENTS.md §12`.

## File Map

| File | Purpose | Engine |
|------|---------|--------|
| `gcl_runner.py` | Baseline runner: generate → critique → decide. Pure stdlib. | Python 3.10+ |
| `gcl_runner_enhanced.py` | Full-featured runner: + StateSnapshot, DegradationDetector, AutonomyRatioTracker, KnowledgeAutoUpdater, trace auto-analysis. | Python 3.10+ |
| `gcl_runner_test.py` | Unittest suite for baseline runner. | stdlib unittest |
| `gcl_auditlog_crosscheck.py` | Phase 3-C: verifies GCL traces against Cloud Audit Logs. | Python 3.10+ |
| `gcl_auditlog_crosscheck_test.py` | Unittest for cross-checker. | stdlib unittest |
| `gcl_passrate_reporter.py` | Phase 4: aggregates GCL traces, pushes to Cloud Monitoring. | Python 3.10+ |
| `gcl_monitoring_alarm_setup.py` | Phase 3-B + 4: idempotent Cloud Monitoring alert policy creator. | Python 3.10+ |
| `README.md` | This file. | — |

## `gcl_runner.py` vs `gcl_runner_enhanced.py`

Use the baseline runner for **fast, dependency-free CI** (e.g., lint-only pre-commit hooks).
Use the enhanced runner for **production observability** (autonomy tracking, state drift detection, failure clustering).

| Feature | `gcl_runner.py` | `gcl_runner_enhanced.py` |
|---------|:---:|:---:|
| Generate → Critique → Decide loop | ✅ | ✅ |
| Dry-run mode | ✅ | ✅ |
| Safety gate (inline secret detection) | ✅ | ✅ |
| StateSnapshot (pre/post drift detection) | — | ✅ |
| DegradationDetector (consecutive-failure threshold) | — | ✅ |
| AutonomyRatioTracker + Alert | — | ✅ |
| KnowledgeAutoUpdater (skills-graph sync) | — | ✅ |
| Structured `log_gcl_event` (14 event types) | — | ✅ |
| Trace auto-analysis (`classify_directory` + `cluster_failures`) | — | ✅ |
| BigQuery upload | — | ✅ |
| External dependencies | None | None (uses stdlib + subprocess) |

## Quick Start

### Baseline Runner (CI / fast feedback)

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
export CLOUDSDK_CORE_PROJECT=my-project

python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet'
echo "exit: $?"  # 0 = PASS, 1 = MAX_ITER, 2 = SAFETY_FAIL
```

### Enhanced Runner (production / observability)

```bash
python3 scripts/gcl_runner_enhanced.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
  --output-dir ./audit-results \
  --trace-to-bq
```

### Dry-Run (Critic-Only Regression)

```bash
python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a' \
  --user-request "delete my-instance" \
  --dry-run
```

### Custom Rubric Path

```bash
python3 scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a' \
  --rubric /path/to/custom-rubric.md \
  --output-dir /custom/audit-dir
```

## Testing

Tests live under `gcp-gcl-runner-ops/tests/` (not in `scripts/`). Run from the repo root:

```bash
python3 -m pytest gcp-gcl-runner-ops/tests/ -q
```

From within the skill directory:

```bash
cd gcp-gcl-runner-ops && python3 -m pytest
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | PASS — GCL completed successfully |
| `1` | MAX_ITER — exceeded `max_iter` without passing |
| `2` | SAFETY_FAIL — command deemed unsafe |
| `3` | EARLY_EXIT — inline secret or pre-flight failure |

## Design Decisions

| Decision | Why |
|----------|-----|
| Pure stdlib | Zero external dependencies, works everywhere |
| Mechanical Critic (not LLM) | Deterministic, CI-friendly, free |
| Subprocess for Generator | Matches `gcloud` CLI as primary path |
| Trace persisted as JSON | `jq`-friendly; downstream tools ingest |
| Regex rubric parsed from file | Adding a new skill = adding a rubric; no code change |
| Enhanced adds zero new deps | All new features built from existing stdlib + subprocess |
