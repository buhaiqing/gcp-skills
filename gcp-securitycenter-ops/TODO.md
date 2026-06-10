# TODO — gcp-securitycenter-ops

## Initial Release Checklist

- [x] Create repository-standard skill directory and frontmatter.
- [x] Document SHOULD/SHOULD NOT trigger boundaries and delegation rules.
- [x] Define variable conventions with `{{env.*}}`, `{{user.*}}`, and `{{output.*}}` in [variables-and-conventions.md](references/variables-and-conventions.md).
- [x] Add centralized JSON paths in [variables-and-conventions.md](references/variables-and-conventions.md).
- [x] Add execution flows for all 12 operations (enable SCC, sources, findings, mute configs, notification configs, BQ exports, custom modules, effective modules, resource value configs, org settings, CSV export) in [execution-flows.md](references/execution-flows.md).
- [x] Add Security Command Center-specific troubleshooting with ≥15 error rows.
- [x] Add monitoring, integration, idempotency, and well-architected references.
- [x] Add GCL rubric and prompt templates.
- [x] Add example config and eval queries (12 should-trigger, 10 should-not-trigger).
- [x] Add load condition annotations to all reference links in SKILL.md.
- [x] Add metadata headers (load_condition, token_cost_estimate, dependencies) to all reference files.
- [x] Move execution flow details to references/execution-flows.md; SKILL.md kept slim (~270 lines, ~5000 tokens).
- [x] Move variable table and JSON paths to references/variables-and-conventions.md.
- [x] Add YAML anchors to example-config.yaml (TE-5).

## Future Enhancements

- [ ] Add advanced FinOps/AIOps references in `references/advanced/` if requested (e.g., FinOps cost analysis for BigQuery export storage, AIOps anomaly detection for finding spike patterns).
- [ ] Add Event Threat Detection and Container Threat Detection deep-dive operation support if Premium tier operations are requested.
- [ ] Add SCC Enterprise tier specifics (attack path simulation, Chronicle integration) if Enterprise tier skills are requested.
- [ ] Add SDK-only operations (custom modules, effective modules, resource value configs) with standalone code snippets in `assets/code-snippets/` if this skill becomes SDK-primary for those operations.
- [ ] Add post-update self-review per [AGENTS.md §11](AGENTS.md#11-post-update-self-review-mandatory).