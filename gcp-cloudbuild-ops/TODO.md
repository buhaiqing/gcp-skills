# TODO — gcp-cloudbuild-ops

## Initial Release Checklist

- ✅ Create repository-standard skill directory and frontmatter.
- ✅ Document SHOULD/SHOULD NOT trigger boundaries and delegation rules.
- ✅ Define variable conventions with `{{env.*}}`, `{{user.*}}`, and `{{output.*}}` in [variables-and-conventions.md](references/variables-and-conventions.md).
- ✅ Add centralized JSON paths in [variables-and-conventions.md](references/variables-and-conventions.md).
- ✅ Add execution flows for submit, list/describe, cancel/retry, trigger CRUD/run, private worker pools, and failure diagnosis in [execution-flows.md](references/execution-flows.md).
- ✅ Add Cloud Build-specific troubleshooting with at least 15 error rows.
- ✅ Add monitoring, integration, idempotency, and well-architected references.
- ✅ Add GCL rubric and prompt templates.
- ✅ Add example config and eval queries (12 should-trigger, 10 should-not-trigger).
- ✅ Update top-level README available-skills table.
- ✅ Add load condition annotations to all reference links in SKILL.md.
- ✅ Add metadata headers (load_condition, token_cost_estimate, dependencies) to all reference files.
- ✅ Move execution flow details to references/execution-flows.md; SKILL.md kept slim (~200 lines, ~3700 tokens).
- ✅ Move variable table and JSON paths to references/variables-and-conventions.md.

## Future Enhancements

- [ ] Add advanced Cloud Build FinOps/AIOps references in `references/advanced/` if requested.
- [ ] Add standalone SDK code snippets if this skill becomes SDK-primary.
