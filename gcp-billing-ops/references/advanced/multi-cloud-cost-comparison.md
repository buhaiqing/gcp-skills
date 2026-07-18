# Multi-Cloud Cost Comparison — FinOps Analysis Framework

> Provides FinOps practitioners with a framework and tooling for comparing costs across Google Cloud, AWS, and Azure — standardized pricing models, TCO analysis, and workload-based cost modeling.

## Table of Contents

1. [Overview](#overview)
2. [Pricing Model Comparison](#pricing-model-comparison)
3. [Service Equivalence Mapping](#service-equivalence-mapping)
4. [Cost Normalization](#cost-normalization)
5. [TCO Analysis Framework](#tco-analysis-framework)
6. [Workload Cost Modeling](#workload-cost-modeling)
7. [Reporting Templates](#reporting-templates)
8. [See Also](#see-also)

## Overview

Multi-cloud cost comparison requires normalizing pricing across providers with different billing models, unit definitions, and discount structures. This guide provides a systematic approach to accurate cross-cloud cost analysis.

### Key Comparison Dimensions

| Dimension | Google Cloud | AWS | Azure |
|-----------|-------------|-----|-------|
| Compute billing | Per vCPU-second | Per vCPU-second | Per vCPU-second |
| Storage | Per GB-month | Per GB-month | Per GB-month |
| Network egress | Per GB | Per GB | Per GB |
| Managed services | Per API call + compute | Per API call + compute | Per API call + compute |

## Pricing Model Comparison

### Compute Pricing Comparison

| Resource | GCP (on-demand) | AWS (on-demand) | Azure (on-demand) |
|----------|-----------------|-----------------|------------------|
| 2 vCPU, 8GB | ~$0.17/hr (e2-medium) | ~$0.17/hr (t3.medium) | ~$0.17/hr (B2s) |
| 4 vCPU, 16GB | ~$0.34/hr (e2-standard-2) | ~$0.34/hr (t3.xlarge) | ~$0.34/hr (B2ms) |
| 8 vCPU, 32GB | ~$0.68/hr (e2-standard-4) | ~$0.68/hr (m5.2xlarge) | ~$0.68/hr (D2s_v3) |
| 16 vCPU, 64GB | ~$1.36/hr (e2-standard-8) | ~$1.36/hr (m5.4xlarge) | ~$1.36/hr (D4s_v3) |

### Storage Pricing Comparison

| Storage Type | GCP | AWS | Azure |
|-------------|-----|-----|-------|
| Hot storage | $0.020/GB/mo | $0.023/GB/mo | $0.018/GB/mo |
| Cold storage | $0.004/GB/mo | $0.0125/GB/mo | $0.01/GB/mo |
| Archive storage | $0.0012/GB/mo | $0.00099/GB/mo | $0.00099/GB/mo |
| Snapshot | $0.05/GB/mo | $0.05/GB/mo | $0.05/GB/mo |

### Network Pricing Comparison

| Traffic Type | GCP | AWS | Azure |
|-------------|-----|-----|-------|
| Intra-region | Free | Free | Free |
| Out to Internet (Americas) | $0.12/GB | $0.09/GB | $0.087/GB |
| Region to Region | $0.08-0.15/GB | $0.02-0.15/GB | $0.05-0.15/GB |
| Cloud CDN | $0.04-0.15/GB | $0.0085-0.085/GB | $0.05-0.15/GB |

## Service Equivalence Mapping

### Core Services Comparison

| Category | Google Cloud | AWS | Azure |
|----------|-------------|-----|-------|
| Compute | Compute Engine | EC2 | Virtual Machines |
| Serverless Compute | Cloud Run / Cloud Functions | Lambda | Azure Functions |
| Container Orchestration | GKE | EKS | AKS |
| Object Storage | Cloud Storage | S3 | Blob Storage |
| Block Storage | Persistent Disk | EBS | Managed Disks |
| File Storage | Filestore | EFS / FSx | Azure Files |
| Managed Database | Cloud SQL | RDS | Azure SQL |
| NoSQL | Firestore / Datastore | DynamoDB | Cosmos DB |
| Data Warehouse | BigQuery | Redshift | Synapse Analytics |
| Message Queue | Pub/Sub | SQS | Service Bus |
| Streaming | Pub/Sub | Kinesis | Event Hubs |
| CDN | Cloud CDN | CloudFront | Azure CDN |
| DNS | Cloud DNS | Route 53 | Azure DNS |
| Load Balancer | Cloud Load Balancing | ELB / ALB / NLB | Load Balancer |
| API Gateway | API Gateway | API Gateway | API Management |

## Cost Normalization

### Currency and Unit Normalization

```python
# normalize_costs.py
import pandas as pd
from datetime import datetime

class CloudCostNormalizer:
    """Normalize costs across cloud providers."""

    def __init__(self, target_currency="USD"):
        self.target_currency = target_currency
        # Exchange rates (as of analysis date)
        self.exchange_rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.79,
            "JPY": 149.50,
        }

    def normalize_units(self, provider, resource_type, quantity):
        """Convert cloud-specific units to standardized units."""
        normalizations = {
            "gcp": {
                "vCPU": {"unit": "vCPU", "factor": 1},
                "GB": {"unit": "GB", "factor": 1},
                "GB-month": {"unit": "GB-mo", "factor": 1},
            },
            "aws": {
                "vCPU": {"unit": "vCPU", "factor": 1},
                "GB": {"unit": "GB", "factor": 1},
                "GB-month": {"unit": "GB-mo", "factor": 1},
            },
            "azure": {
                "vCPU": {"unit": "vCPU", "factor": 1},
                "GB": {"unit": "GB", "factor": 1},
                "GB-month": {"unit": "GB-mo", "factor": 1},
            },
        }
        return normalizations.get(provider, {}).get(resource_type, {}).get("factor", 1) * quantity

    def convert_currency(self, amount, from_currency):
        """Convert amount to target currency."""
        rate = self.exchange_rates.get(from_currency, 1.0)
        target_rate = self.exchange_rates.get(self.target_currency, 1.0)
        return amount * (rate / target_rate)

    def normalize_monthly(self, hourly_cost):
        """Convert hourly to monthly (730 hours)."""
        return hourly_cost * 730
```

### Standardized Cost Report Generation

```bash
#!/bin/bash
# generate-cross-cloud-report.sh

OUTPUT_DIR="./cost-reports"
mkdir -p $OUTPUT_DIR

# GCP Costs (from billing export)
bq query --nouse_legacy_sql "
SELECT
  'GCP' AS provider,
  service.description AS service,
  ROUND(SUM(cost), 2) AS monthly_cost
FROM \`gcp_billing_export\`
WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY 1, 2
" > $OUTPUT_DIR/gcp_costs.json

# AWS Costs (from Cost Explorer export)
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=SERVICE > $OUTPUT_DIR/aws_costs.json

# Azure Costs (from Cost Management export)
az cost management query \
  --time-period-type MonthToDate \
  --dataset-grouping name service \
  --type actualcost \
  --output table > $OUTPUT_DIR/azure_costs.json

echo "Cross-cloud report generated in $OUTPUT_DIR"
```

## TCO Analysis Framework

### Total Cost of Ownership Components

| Component | Description | GCP | AWS | Azure |
|-----------|-------------|-----|-----|-------|
| Compute | VM/instance costs | | | |
| Storage | Object, block, file | | | |
| Network | Data transfer, CDN | | | |
| Managed Services | Databases, queues, etc. | | | |
| Support | Basic/Production/Premier | $0-$100k+/mo | $0-$100k+/mo | $0-$100k+/mo |
| Personnel | Operations overhead | | | |
| Licensing | Third-party licenses | | | |
| Compliance | Audit, certifications | | | |

### TCO Calculator

```python
# tco_calculator.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class WorkloadProfile:
    name: str
    compute_vcpus: int
    compute_hours_per_month: float
    storage_gb: float
    network_egress_gb: float
    managed_services_pct: float  # % of workload using managed services

@dataclass
class TCOAnalysis:
    provider: str
    compute_cost: float
    storage_cost: float
    network_cost: float
    managed_services_cost: float
    support_cost: float
    total: float

def calculate_tco(provider: str, workload: WorkloadProfile, pricing: Dict) -> TCOAnalysis:
    """Calculate TCO for a workload on a specific provider."""

    # Compute costs
    hourly_rate = pricing["compute_rate_per_vcpu_hour"]
    compute_cost = workload.compute_vcpus * workload.compute_hours_per_month * hourly_rate

    # Storage costs
    storage_cost = workload.storage_gb * pricing["storage_rate_per_gb_month"]

    # Network costs
    network_cost = workload.network_egress_gb * pricing["network_rate_per_gb"]

    # Managed services (typically 20-40% premium over raw compute)
    managed_services_cost = compute_cost * workload.managed_services_pct * pricing["managed_premium"]

    # Support costs (simplified tier model)
    support_cost = pricing["support_tiers"].get(
        "enterprise" if compute_cost > 50000 else "production", 0
    )

    total = compute_cost + storage_cost + network_cost + managed_services_cost + support_cost

    return TCOAnalysis(
        provider=provider,
        compute_cost=compute_cost,
        storage_cost=storage_cost,
        network_cost=network_cost,
        managed_services_cost=managed_services_cost,
        support_cost=support_cost,
        total=total
    )
```

## Workload Cost Modeling

### Comparative Workload Analysis

```bash
#!/bin/bash
# workload-comparison.sh

WORKLOAD_VCPU=8
WORKLOAD_STORAGE_GB=500
WORKLOAD_EGRESS_GB=100

# GCP Cost Estimate
GCP_COMPUTE=$(echo "scale=2; $WORKLOAD_VCPU * 0.068 * 730" | bc)  # e2-standard-4
GCP_STORAGE=$(echo "scale=2; $WORKLOAD_STORAGE_GB * 0.02" | bc)  # Standard storage
GCP_NETWORK=$(echo "scale=2; $WORKLOAD_EGRESS_GB * 0.12" | bc)
GCP_TOTAL=$(echo "scale=2; $GCP_COMPUTE + $GCP_STORAGE + $GCP_NETWORK" | bc)

# AWS Cost Estimate
AWS_COMPUTE=$(echo "scale=2; $WORKLOAD_VCPU * 0.0768 * 730" | bc)  # m5.2xlarge
AWS_STORAGE=$(echo "scale=2; $WORKLOAD_STORAGE_GB * 0.023" | bc)  # S3 Standard
AWS_NETWORK=$(echo "scale=2; $WORKLOAD_EGRESS_GB * 0.09" | bc)
AWS_TOTAL=$(echo "scale=2; $AWS_COMPUTE + $AWS_STORAGE + $AWS_NETWORK" | bc)

# Azure Cost Estimate
AZURE_COMPUTE=$(echo "scale=2; $WORKLOAD_VCPU * 0.0768 * 730" | bc)  # D2s_v3
AZURE_STORAGE=$(echo "scale=2; $WORKLOAD_STORAGE_GB * 0.018" | bc)  # Blob Hot
AZURE_NETWORK=$(echo "scale=2; $WORKLOAD_EGRESS_GB * 0.087" | bc)
AZURE_TOTAL=$(echo "scale=2; $AZURE_COMPUTE + $AZURE_STORAGE + $AZURE_NETWORK" | bc)

echo "Monthly Cost Comparison for ${WORKLOAD_VCPU}vCPU/${WORKLOAD_STORAGE_GB}GB Workload:"
echo "GCP:   \$${GCP_TOTAL}"
echo "AWS:   \$${AWS_TOTAL}"
echo "Azure: \$${AZURE_TOTAL}"

# Identify best option
echo ""
echo "Recommendation: $(echo "$GCP_TOTAL $AWS_TOTAL $AZURE_TOTAL" | \
  awk '{if($1<$2 && $1<$3) print "GCP"; else if($2<$1 && $2<$3) print "AWS"; else print "Azure"}')"
```

## Reporting Templates

### Monthly Cross-Cloud Cost Report

```markdown
# Multi-Cloud Cost Report — $(date +%Y-%m)

## Executive Summary
| Metric | GCP | AWS | Azure |
|--------|-----|-----|-------|
| Total Spend | $X | $Y | $Z |
| MoM Change | +X% | +Y% | +Z% |
| vs Budget | On Track / Over | On Track / Over | On Track / Over |

## Compute Cost Comparison
| Workload Type | GCP | AWS | Azure | Lowest |
|---------------|-----|-----|-------|--------|
| Web Servers | | | | |
| Databases | | | | |
| Batch Processing | | | | |
| Serverless | | | | |

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]
```

## See Also

- [FinOps Cost Analysis](../finops-cost-analysis.md)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [AWS Pricing Calculator](https://calculator.aws)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
