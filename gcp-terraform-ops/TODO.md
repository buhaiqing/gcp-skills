# TODO — gcp-terraform-ops

## Initial Release Checklist

- [x] Create repository-standard skill directory and frontmatter.
- [x] Document SHOULD/SHOULD NOT trigger boundaries and delegation rules.
- [x] Define variable conventions with `{{env.*}}`, `{{user.*}}`, and `{{output.*}}` in [variables-and-conventions.md](references/variables-and-conventions.md).
- [x] Add centralized environment paths in [variables-and-conventions.md](references/variables-and-conventions.md).
- [x] Add execution flows for all 8 operations (init, validate, plan, apply, destroy, import, state, workspace, output/show) in [execution-flows.md](references/execution-flows.md).
- [x] Add Terraform-specific troubleshooting with ≥15 error rows.
- [x] Add monitoring, integration, idempotency, and well-architected references.
- [x] Add GCL rubric and prompt templates.
- [x] Add example config and eval queries (22 should-trigger, 10 should-not-trigger).
- [x] Add environments/{dev,staging,prod}/ directory structure with example .tf files.
- [x] Add load condition annotations to all reference links in SKILL.md.
- [x] Add metadata headers (load_condition, token_cost_estimate, dependencies) to all reference files.
- [x] Move execution flow details to references/execution-flows.md; SKILL.md kept slim (~270 lines, ~5000 tokens).
- [x] Move variable table and environment paths to references/variables-and-conventions.md.
- [x] Add YAML anchors to example-config.yaml (TE-5).
- [x] Add test suite in `assets/code-snippets/test_terraform_ops.py` (Tier 0/1/eval_q/gcl).
- [x] Directory isolation model: each environment has its own GCS backend bucket.
- [x] Provider version pinning enforced in all environments.
- [x] GCL required for apply/destroy/import/state operations with dual safety gate.

## Future Enhancements

- [ ] Add `references/advanced/` directory for FinOps cost estimation from plan output (resource cost calculator) and AIOps drift detection patterns.
- [ ] Add standalone Terraform validation scripts in `assets/code-snippets/` for CI/CD integration.
- [ ] Add `terraform import` operation coverage for more GCP resource types (Cloud SQL, GKE, Cloud Storage, BigQuery).
- [ ] Add workspace-based team collaboration workflow if requested (current skill uses directory isolation as primary model).
- [ ] Add provider version upgrade runbook with `terraform init -upgrade` and state migration guide.
- [ ] Add post-update self-review per [AGENTS.md §11](AGENTS.md#11-post-update-self-review-mandatory).
- [ ] Verify exact GCS storage costs for state files across environments and update monitoring.md with current GCP pricing.
- [ ] Add HCL module authoring guidance if module development workflow is requested.