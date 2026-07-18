# FinOps Cost Estimation from Terraform Plan

> Parse `terraform show -json plan` output to estimate infrastructure costs using Infracost or GCP Pricing API, integrate into CI/CD pipeline.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infracost Integration](#infracost-integration)
4. [GCP Pricing API Cost Estimation](#gcp-pricing-api-cost-estimation)
5. [CI/CD Integration](#cicd-integration)
6. [Cost Baseline Management](#cost-baseline-management)
7. [Breakdown by Resource Type](#breakdown-by-resource-type)
8. [See Also](#see-also)

## Overview

FinOps cost estimation from Terraform plans enables teams to catch cost implications **before** resources are provisioned. This runbook covers two approaches:

- **Infracost** (recommended): Cloud-agnostic, supports 120+ resource types, free tier available
- **GCP Pricing API**: Native GCP, requires mapping Terraform resource types to SKU IDs

## Prerequisites

```bash
# Install Infracost
brew install infracost  # macOS
# or: curl -fsSL https://infracost.io/install.sh | sh

# Authenticate to GCP
gcloud auth application-default login

# Set project
export CLOUDSDK_CORE_PROJECT="your-project-id"
```

## Infracost Integration

### Install Infracost Terraform Plan Hook

```bash
# Add to your CI/CD pipeline before terraform apply
infracost breakdown --path . \
  --terraform-plan-file ./tfplan \
  --show-skipped \
  --out-file /tmp/infracost.json

# Compare with previous run
infracost diff --path /tmp/infracost.json \
  --compare-to /tmp/infracost-baseline.json
```

### Terraform Plan to JSON

```bash
# Generate JSON plan (requires terraform init first)
cd environments/dev/
terraform init -backend=false
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json

# Infracost analysis
infracost breakdown --terraform-plan-file tfplan.json \
  --project-name "dev-environment" \
  --show-skipped
```

### GitHub Actions Example

```yaml
# .github/workflows/terraform-plan.yml
name: Terraform Plan with Cost Estimation

on:
  pull_request:
    paths:
      - 'environments/**'
      - 'modules/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Setup Infracost
        uses: infracost/actions/setup@v3
        with:
          api_key: ${{ secrets.INFRACOST_API_KEY }}

      - name: Terraform Init
        run: terraform init
        env:
          TF_VAR_project_id: ${{ secrets.GCP_PROJECT_ID }}

      - name: Terraform Plan
        run: terraform plan -out=tfplan

      - name: Generate JSON Plan
        run: terraform show -json tfplan > tfplan.json

      - name: Infracost Breakdown
        uses: infracost/actions/breakdown@v3
        with:
          path: ./tfplan.json
          terraform_plan_file: true
          github_comment: true

      - name: Infracost Diff
        uses: infracost/actions/diff@v3
        with:
          path: ./tfplan.json
          terraform_plan_file: true
          github_comment: true
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
infracost:
  image:
    name: infracost/infracost:0.10
    entrypoint: [""]
  script:
    - terraform init -backend=false
    - terraform plan -out=tfplan
    - terraform show -json tfplan > tfplan.json
    - infracost breakdown --terraform-plan-file tfplan.json --path .
    - infracost diff --terraform-plan-file tfplan.json --path .
  variables:
    INFRACOST_API_KEY: ${INFRACOST_API_KEY}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## GCP Pricing API Cost Estimation

### Get GCP SKU Pricing

```bash
# Get access token
TOKEN=$(gcloud auth print-access-token)

# Query compute instance pricing
curl -s -X GET \
  "https://cloudbilling.googleapis.com/v1/services/6F81-5424-09FA/skus" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" | jq '.skus[] | select(.description | contains("N2 Standard")) | {description, pricingInfo}'
```

### Custom Cost Estimation Script

```python
#!/usr/bin/env python3
"""Estimate GCP costs from terraform plan JSON."""
import json
import sys
from pathlib import Path

# Resource type to GCP service mapping
RESOURCE_SERVICE_MAP = {
    "google_compute_instance": "compute",
    "google_compute_instance_template": "compute",
    "google_sql_database_instance": "cloudsql",
    "google_container_cluster": "kubernetes",
    "google_storage_bucket": "storage",
    "google_bigquery_dataset": "bigquery",
}

def estimate_cost_from_plan(plan_json: dict) -> dict:
    """Parse plan JSON and estimate monthly costs."""
    total_monthly_cost = 0.0
    breakdown = {}

    for resource in plan_json.get("values", {}).get("root_module", {}).get("resources", []):
        resource_type = resource.get("type", "")
        values = resource.get("values", {})

        cost = calculate_resource_cost(resource_type, values)
        if cost > 0:
            breakdown[resource_type] = breakdown.get(resource_type, 0) + cost
            total_monthly_cost += cost

    return {"total_monthly_cost": total_monthly_cost, "breakdown": breakdown}

def calculate_resource_cost(resource_type: str, values: dict) -> float:
    """Calculate monthly cost for a resource."""
    # Simplified pricing - use GCP Pricing API for production
    INSTANCE_COSTS = {
        "n2-standard-2": 0.10,
        "n2-standard-4": 0.20,
        "n2-standard-8": 0.40,
    }

    if resource_type == "google_compute_instance":
        machine_type = values.get("machine_type", "n2-standard-2")
        count = values.get("count", 1)
        preemptible = values.get("scheduling", {}).get("preemptible", False)
        hourly_rate = INSTANCE_COSTS.get(machine_type, 0.10)
        if preemptible:
            hourly_rate *= 0.2  # 80% discount
        return hourly_rate * count * 730  # ~730 hours/month

    elif resource_type == "google_sql_database_instance":
        tier = values.get("tier", "db-n1-standard-2")
        count = values.get("count", 1)
        return 0.05 * count * 730  # Simplified

    elif resource_type == "google_storage_bucket":
        storage_gb = values.get("storage_class", "STANDARD") == "STANDARD" and 0.020 or 0.010
        return storage_gb * 50 * 730  # Assume 50GB

    return 0.0

if __name__ == "__main__":
    plan_file = Path(sys.argv[1])
    plan_json = json.loads(plan_file.read_text())
    result = estimate_cost_from_plan(plan_json)
    print(json.dumps(result, indent=2))
```

## CI/CD Integration

### Pre-Apply Cost Gate

```bash
#!/bin/bash
# pre-apply-cost-gate.sh — Run before terraform apply

set -euo pipefail

PLAN_FILE="${1:-tfplan}"
MAX_MONTHLY_COST="${MAX_MONTHLY_COST:-10000}"

# Generate JSON plan
terraform show -json "$PLAN_FILE" > plan.json

# Run cost estimation
python3 scripts/estimate_cost.py plan.json > cost.json

MONTHLY_COST=$(jq -r '.total_monthly_cost' cost.json)

echo "Estimated monthly cost: $${MONTHLY_COST}"
echo "Maximum allowed: $${MAX_MONTHLY_COST}"

if (( $(echo "$MONTHLY_COST > $MAX_MONTHLY_COST" | bc -l) )); then
    echo "ERROR: Cost exceeds threshold"
    exit 1
fi

echo "Cost check passed"
jq '.breakdown' cost.json
```

### Cost Diff in PR Comments

```bash
#!/bin/bash
# post-plan-cost-comment.sh — Post cost diff to PR

set -euo pipefail

BASELINE_FILE="${BASELINE_FILE:-/tmp/cost-baseline.json}"
CURRENT_FILE="${CURRENT_FILE:-/tmp/cost-current.json}"
PR_NUMBER="${PR_NUMBER:-}"

if [ ! -f "$BASELINE_FILE" ]; then
    # First run - save baseline
    cp "$CURRENT_FILE" "$BASELINE_FILE"
    exit 0
fi

# Generate diff
infracost diff --path "$CURRENT_FILE" --compare-to "$BASELINE_FILE" || true

# Update baseline
cp "$CURRENT_FILE" "$BASELINE_FILE"
```

## Cost Baseline Management

### Store Cost Baseline in GCS

```bash
# Upload cost baseline after successful apply
BUCKET="gs://tf-state-${CLOUDSDK_CORE_PROJECT}/cost-baselines"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Save current state cost
infracost breakdown --path . --show-skipped > /tmp/current-cost.json
gsutil cp /tmp/current-cost.json "${BUCKET}/dev-${TIMESTAMP}.json"

# Update latest baseline
gsutil cp /tmp/current-cost.json "${BUCKET}/dev-latest.json"
```

### Terratest Example

```go
// cost_estimation_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/gruntwork-io/terratest/modules/shell"
    "github.com/stretchr/testify/assert"
)

func TestTerraformCostEstimate(t *testing.T) {
    terraformOptions := &terraform.Options{
        TerraformDir: "../environments/dev",
    }

    // Plan and generate JSON
    planFile := "tfplan"
    terraform.Init(t, terraformOptions)
    terraform.Plan(t, terraformOptions, terraform.WithPlanFile(planFile))
    shell.RunCommand(t, "terraform show -json "+planFile+" > plan.json")

    // Run cost estimation
    output := shell.RunCommandAndGetOutput(t,
        "python3 ../scripts/estimate_cost.py plan.json")

    // Parse and assert
    // (simplified - use JSON parsing in production)
    assert.NotEmpty(t, output)
}
```

## Breakdown by Resource Type

| Resource Type | Cost Driver | Est. Monthly Cost |
|---------------|-------------|-------------------|
| `google_compute_instance` | machine_type, count, preemptible | $0.05-$4/hr per instance |
| `google_sql_database_instance` | tier, storage, backup | $50-$500/month |
| `google_container_cluster` | node_count, machine_type | $50-$500/month |
| `google_storage_bucket` | storage_gb, access_class | $0.02/GB |
| `google_bigquery_dataset` | storage, queries | $0.02/GB + query costs |

## See Also

- [Infracost Documentation](https://www.infracost.io/docs/)
- [GCP Pricing API](https://cloud.google.com/billing/v1/reference/rest)
- [Terraform Cost Estimation](https://developer.hashicorp.com/terraform/tutorials/cost-estimation)
- [Well-Architected Cost Pillar](../well-architected-assessment.md#cost)
