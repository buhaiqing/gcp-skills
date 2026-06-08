# Skill CLI Dry-Run Validation Harness

Automated validation that Skill-generated commands are syntactically correct, structurally valid, and follow safety conventions.

## Usage

```bash
# Validate a single skill
python3 scripts/eval_dryrun.py gcp-bigquery-ops

# Validate all skills
python3 scripts/eval_dryrun.py --all

# Filter to specific query
python3 scripts/eval_dryrun.py gcp-pubsub-ops --query "create a topic"

# JSON output for CI integration
python3 scripts/eval_dryrun.py --all --json
```

## Validation Layers

| Layer | Method | What it checks | Reliability |
|-------|--------|---------------|-------------|
| **L1** | Regex/pattern matching | Command syntax, project flags, credential leaks, expected pattern match | High |
| **L2** | Actual dry-run execution | `bq query --dry_run` estimates cost without executing | Highest (but requires GCP credentials) |
| **L3** | jq path validation | All `.field` extractions work against mock JSON data | High |
| **L4** | Safety gate check | Destructive operations (delete/drop/rm) require user confirmation | Highest |

## How it works

1. **Load** `eval_queries.json` from the skill's `assets/` directory
2. **Simulate LLM** generating a command from each natural language query (Phase 1 uses keyword mapping; Phase 2+ calls real LLM)
3. **Validate** the generated command through L1-L4 layers
4. **Report** pass/fail per test case with detailed diagnostics

## eval_queries.json format

Enhanced from the original format with new fields:

```json
{
  "query": "run a SQL query on my table",
  "should_trigger": true,
  "expected_cmd_pattern": "bq query.*--use_legacy_sql=false",
  "dry_run_supported": true,
  "safety_check": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | ✅ | Natural language user input |
| `should_trigger` | bool | ✅ | Whether this skill should activate |
| `expected_cmd_pattern` | string | Optional | Regex pattern the generated command should match |
| `dry_run_supported` | bool | Optional | Whether this command supports `--dry_run`/`--dry-run` |
| `safety_check` | bool | Optional | Whether this is a destructive operation requiring safety gates |

## CI Integration

```yaml
# Example GitHub Actions step
- name: Validate Skills
  run: python3 scripts/eval_dryrun.py --all --json | tee eval-results.json
```

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Done | L1 structure + L3 JSON path validation, keyword-based LLM simulation |
| **Phase 2** | TODO | L2 real dry-run execution, LLM-based command generation |
| **Phase 3** | TODO | L4 safety gate enforcement, L5 emulator-based end-to-end testing |

## Architecture

```
eval_queries.json ──┐
                     ▼
SKILL.md ──► simulate_llm() ──► validate_structure() ──► L1 result
                             ├─► validate_dry_run() ───► L2 result
                             ├─► validate_json_paths()─► L3 result
                             └─► check_safety_gates() ─► L4 result
                                                       │
                                                       ▼
                                                 Pass/Fail report
```
