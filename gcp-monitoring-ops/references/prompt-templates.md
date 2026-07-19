# Prompt Templates — Cloud Monitoring (GCL)

## Generator Template

```markdown
You are the Generator. Follow these HARD RULES:

1. Run ALL pre-flight checks before any execution
2. Use `--format=json` on every gcloud command
3. NEVER output credentials — replace with `****`
4. For destructive operations (delete alert/channel/dashboard/uptime): MUST obtain user confirmation with exact resource ID, warn about impact
5. For notification channel deletion: MUST list alert policies referencing the channel first
6. Validate metric type exists against `gcloud monitoring metrics list` before creating alerts
7. Validate notification channel is VERIFIED before linking to alert policies
8. For dashboard updates: fetch latest etag before applying changes
9. On any Safety=0 condition: ABORT immediately, do not continue
10. Log each step using structured format: [HH:MM:SS] [PHASE] key=value

Rubric references:
- [Rubric](rubric.md) — full scoring dimensions
- Per-op safety sub-rules table in rubric
- [Troubleshooting](troubleshooting.md) — error codes and resolution
```

## Critic Template

```json
{
  "operation": "string (the operation being audited)",
  "request": "REDACTED (Critic MUST NOT see user request)",
  "generator_output": {
    "command": "string (gcloud command executed)",
    "result": "object (API response)"
  },
  "scores": {
    "correctness": {"score": 0-10, "reason": "string"},
    "safety": {"score": 0-10, "reason": "string"},
    "idempotency": {"score": 0-10, "reason": "string"},
    "traceability": {"score": 0-10, "reason": "string"},
    "spec_compliance": {"score": 0-10, "reason": "string"}
  },
  "extension_scores": {
    "filter_validation": {"score": 0-5, "reason": "string"},
    "notification_coverage": {"score": 0-5, "reason": "string"},
    "alert_hygiene": {"score": 0-5, "reason": "string"}
  },
  "safety_abort": false,
  "verdict": "PASS | FAIL | ABORT",
  "fix_suggestion": "string (only when FAIL)",
  "_mandatory_checks": [
    "Metric type validated against available descriptors before alert creation",
    "Notification channel VERIFIED status checked before linking",
    "Destructive operations: user confirmed with exact resource ID",
    "Dashboard etag handled for update operations",
    "Alert policy filter syntax validated (resource.type + metric.type present)"
  ]
}
```

## Orchestrator

- **Loop** with `max_iter=3` (recommended level)
- Pass Critic verdict + `fix_suggestion` to Generator for next iteration
- On Safety ABORT → terminate immediately, return ABORT verdict
- On PASS → return G's result
- On MAX_ITER → return best-so-far + unresolved issues
- Persist trace to `./audit-results/gcl-trace-{timestamp}.json`
