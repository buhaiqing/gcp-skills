<!--
============================================================================
INSTANTIATION GUIDE — template-finops.md
============================================================================
This is a STANDALONE copy-paste template. To use it for a new product skill:

1. Copy this file to: gcp-<product>-ops/references/advanced/finops-<product>-cost.md
2. Replace every {{...}} placeholder:
   - {{PRODUCT}}      → e.g. Cloud Storage / BigQuery
   - {{user.*}}       → operator-supplied runtime values (ask once)
   - {{env.*}}        → never ask; read from environment
3. Fill the Cost Drivers table with real pricing for {{PRODUCT}} (use live queries where
   possible per TE-1; static prices only as a fallback).
4. Replace the gcloud/bq/gsutil queries with the product's real cost-discovery commands.
5. Keep Dry-Run/Threshold Gating and Troubleshooting sections structurally intact.
6. Do NOT print credentials.

Models: gcp-gcs-ops/references/advanced/finops-storage-cost.md
        gcp-bigquery-ops/references/advanced/finops-bigquery-cost.md
============================================================================
-->

# FinOps Cost Optimization — {{PRODUCT}}

> Provides administrators with a complete guide to optimizing costs associated with {{PRODUCT}} — cost drivers, idle/waste detection, sizing/commitment recommendations, and threshold gating.

## Table of Contents

1. [Overview](#overview)
2. [Cost Drivers](#cost-drivers)
3. [Idle / Waste Detection](#idle--waste-detection)
4. [Sizing / Commitment Recommendations](#sizing--commitment-recommendations)
5. [Dry-Run / Threshold Gating](#dry-run--threshold-gating)
6. [Troubleshooting High Costs](#troubleshooting-high-costs)
7. [See Also](#see-also)

## Overview

{{PRODUCT}} costs primarily come from:

- **{{cost_component_1}}** — {{desc_1}}
- **{{cost_component_2}}** — {{desc_2}}
- **{{cost_component_3}}** — {{desc_3}}

Optimizing these costs can reduce {{PRODUCT}} spend by 40-70% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| {{resource_1}} | {{pricing_1}} | {{cost_1}} | {{opt_1}} |
| {{resource_2}} | {{pricing_2}} | {{cost_2}} | {{opt_2}} |
| {{resource_3}} | {{pricing_3}} | {{cost_3}} | {{opt_3}} |
| {{resource_4}} | {{pricing_4}} | {{cost_4}} | {{opt_4}} |

## Idle / Waste Detection

### Detect idle / underutilized resources

```bash
# List {{PRODUCT}} resources and flag idle (no recent activity / low utilization)
gcloud {{product_cli_path}} list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" \
  | jq -r '{{idle_filter_jq}}'
```

### Detect waste (over-provisioned / orphaned)

```bash
# Flag orphaned / unattached resources
gcloud {{product_cli_path}} list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="{{waste_filter}}" \
  --format="json"
```

## Sizing / Commitment Recommendations

### Right-sizing analysis

```bash
# Analyze utilization to recommend right size
gcloud {{product_cli_path}} describe "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{{sizing_jq}}'
```

### Commitment / reservation recommendation

| Signal | Threshold | Recommendation |
|--------|-----------|----------------|
| Steady baseline usage ≥ {{baseline_pct}}% of peak | sustained {{window}} | Purchase committed-use discount / reservation |
| Bursty usage | intermittent | Stay on-demand |
| Idle ≥ {{idle_pct}}% | {{window}} | Downsize or delete |

## Dry-Run / Threshold Gating

> Mirror the BigQuery FinOps gating model: every cost-reducing mutation is dry-run first and gated by a threshold before apply.

### Dry-run

```bash
RESOURCE="{{user.resource_name}}"
echo "[DRY-RUN] Would apply cost optimization:"
echo "  gcloud {{product_cli_path}} update \"$RESOURCE\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Estimated monthly saving: {{est_saving}}"
```

### Threshold gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Saving ≥ threshold | `est_saving` ≥ `{{user.min_saving_threshold}}` | HALT — below threshold, skip |
| No data loss | optimization is reversible / non-destructive | HALT — destructive optimization needs confirmation |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

### Apply + validate

```bash
gcloud {{product_cli_path}} update "$RESOURCE" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
# Validate cost impact via billing export / pricing API
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| {{issue_1}} | {{cause_1}} | {{solution_1}} |
| {{issue_2}} | {{cause_2}} | {{solution_2}} |
| {{issue_3}} | {{cause_3}} | {{solution_3}} |

### Cost Investigation

```bash
# Find top cost contributors
gcloud {{product_cli_path}} list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{{top_cost_jq}}'
```

## See Also

- [{{PRODUCT}} Monitoring](../monitoring.md)
- [{{PRODUCT}} Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
