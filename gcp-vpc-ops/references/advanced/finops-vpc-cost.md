# FinOps Cost Optimization — Google Cloud VPC

> Provides network administrators with a complete guide to optimizing costs associated with Google Cloud VPC networking — NAT gateways, VPN tunnels, VPC Flow Logs, data transfer, and Shared VPC architecture.

## Table of Contents

1. [Overview](#overview)
2. [VPC Cost Model](#vpc-cost-model)
3. [NAT Gateway Optimization](#nat-gateway-optimization)
4. [VPN Tunnel Optimization](#vpn-tunnel-optimization)
5. [VPC Flow Logs Optimization](#vpc-flow-logs-optimization)
6. [Data Transfer Costs](#data-transfer-costs)
7. [Shared VPC Cost Benefits](#shared-vpc-cost-benefits)
8. [Cost Monitoring](#cost-monitoring)
9. [Automated Cost Control](#automated-cost-control)
10. [Troubleshooting High Costs](#troubleshooting-high-costs)
11. [See Also](#see-also)

## Overview

VPC networking costs in Google Cloud primarily come from:

- **NAT Gateway** — per-hour charge per gateway + data processing
- **VPN Tunnels** — per-hour charge per tunnel
- **VPC Flow Logs** — per-GB ingestion cost
- **Data Transfer** — egress charges between zones/regions
- **IP Addresses** — static IP charges (if not in use)

Optimizing these costs can reduce networking spend by 30-60% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| Cloud NAT | $0.045/hr + $0.045/GB data | $30-50/gateway | 40-60% |
| VPN Tunnel | $0.05/hr | $36/tunnel | 50-70% |
| VPC Flow Logs | $0.50/GB ingested | $10-100/project | 30-50% |
| Data Transfer (egress) | $0.12/GB (to internet) | Varies widely | 20-40% |
| Static IP (unused) | $0.01/hr | $7.20/IP | 100% |

## VPC Cost Model

### Pricing Breakdown

| Resource | Cost Component | Rate |
|----------|---------------|------|
| VPC Network | Usage | Free |
| Subnet | Usage | Free |
| Firewall Rules | Usage | Free (API calls only) |
| Routes | Usage | Free (API calls only) |
| Cloud Router | Usage | Free |
| Cloud NAT | Per-hour | $0.045/gateway |
| Cloud NAT | Data processing | $0.045/GB |
| VPN Tunnel (HA) | Per-hour | $0.05/tunnel (2 tunnels minimum) |
| VPN Tunnel (Classic) | Per-hour | $0.05/tunnel |
| VPC Flow Logs | Ingestion | $0.50/GB |
| Static IP (in use) | Per-hour | $0.01 |
| Static IP (unused) | Per-hour | $0.01 |

### Cost Calculator

```bash
# Monthly NAT gateway cost (one gateway)
echo "NAT cost: $(echo "30 * 24 * 0.045 + 100 * 0.045" | bc)"
# = $32.40 + $4.50 = $36.90/month

# Monthly VPN tunnel cost (one tunnel)
echo "VPN cost: $(echo "30 * 24 * 0.05" | bc)"
# = $36.00/month

# Monthly Flow Logs cost (10GB ingested)
echo "Flow Logs cost: $(echo "10 * 0.50" | bc)"
# = $5.00/month
```

## NAT Gateway Optimization

### Right-Sizing NAT Gateways

**Problem:** Each Cloud NAT gateway costs $0.045/hr ($32.40/month) plus data processing.

**Solution:**
- **Single NAT per region** — One NAT gateway can serve all subnets in a region
- **Shared NAT across projects** — Use Shared VPC for a single NAT
- **Avoid NAT for GKE** — Use Private Clusters + Cloud NAT for egress only
- **Downsize during off-peak** — Temporarily remove NAT gateways for dev environments

**Cost Impact:**
```
Before: 3 NAT gateways (dev, staging, prod) = $97.20/month
After:  1 NAT gateway (shared) = $32.40/month
Savings: $64.80/month (67%)
```

### NAT Configuration Best Practices

| Practice | Savings | Implementation |
|----------|---------|----------------|
| Shared VPC NAT | 50-60% | Use host project NAT for all service projects |
| Auto-scaling NAT IPs | 0-10% | `--nat-ip-allocate-mode=AUTO_ONLY` |
| Manual NAT IPs (static) | 10-20% | Pre-allocate static IPs for consistent pricing |
| Delete idle NATs | 100% on idle | Remove NAT from non-production environments |

### Automate NAT Cleanup

```bash
# List all NAT gateways with last activity
gcloud compute routers nats list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --format="table(name, router, natIpAllocateOption)"

# Delete unused NAT (off-peak, dev environment)
gcloud compute routers nats delete "{{user.nat_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --quiet
```

## VPN Tunnel Optimization

### Tunnel Lifecycle Management

**Problem:** Each HA VPN tunnel costs $0.05/hr ($36/month), and HA VPN requires at least 2 tunnels ($72/month).

**Solution:**
- **Use Classic VPN** for non-critical connections (1 tunnel minimum)
- **Shut down tunnels during maintenance** — delete tunnels when not needed
- **Consolidate tunnels** — One VPN connection per region, not per VPC
- **Use Cloud Interconnect** for high-bandwidth (>1 Gbps) permanent connections

**Cost Comparison:**
```
Connection Type    | Monthly Cost | Bandwidth | Use Case
Classic VPN        | $36          | 1.5 Gbps  | Dev/test, low bandwidth
HA VPN             | $72          | 3 Gbps    | Production, HA required
Dedicated Interconnect | $450 (port) + $0.04/GB | 10 Gbps | Large-scale, high bandwidth
Partner Interconnect   | $45 (VLAN) + $0.04/GB  | 1-10 Gbps | Medium bandwidth
```

### VPN Tunnel Audit

```bash
# List all VPN tunnels and their status
gcloud compute vpn-tunnels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name, region, status, peerAddress)"

# Find tunnels not in ESTABLISHED state
gcloud compute vpn-tunnels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="status != ESTABLISHED" \
  --format="table(name, status)"
```

**Action:** Delete tunnels that are not `ESTABLISHED` and no longer needed.

### Automated Tunnel Cleanup

```bash
#!/bin/bash
# Clean up non-established VPN tunnels older than 30 days
gcloud compute vpn-tunnels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="status != ESTABLISHED AND creationTimestamp < -P30D" \
  --format="value(name,region)" | \
while read name region; do
  gcloud compute vpn-tunnels delete "$name" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --region="$region" \
    --quiet
  echo "Deleted stale tunnel: $name"
done
```

## VPC Flow Logs Optimization

### Sampling Rate Tuning

**Problem:** VPC Flow Logs cost $0.50/GB ingested. High-traffic subnets can generate significant costs.

**Solution:**
- **Reduce sampling rate** — Use `--flow-sampling=0.5` for 50% sampling
- **Disable for low-value subnets** — Turn off flow logs for non-critical subnets
- **Aggregate logs** — Use a single log sink for all flow logs

**Cost Impact:**
```
Before: All subnets, 100% sampling, 100GB/month = $50.00/month
After:  Critical subnets only, 50% sampling, 20GB/month = $10.00/month
Savings: $40.00/month (80%)
```

### Configuration

```bash
# Enable flow logs with reduced sampling
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --enable-flow-logs \
  --logging-aggregation-interval=INTERVAL_5_SEC \
  --logging-flow-sampling=0.5 \
  --logging-metadata=INCLUDE_ALL_METADATA

# Disable flow logs for non-critical subnet
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --no-enable-flow-logs
```

## Data Transfer Costs

### Egress Cost Optimization

| Source | Destination | Cost/GB | Optimization |
|--------|-------------|---------|--------------|
| Same zone | Same zone | Free | Keep resources co-located |
| Same region | Different zone | $0.01 | Acceptable for HA |
| Different region (US) | Different region | $0.02 | Use Cloud CDN |
| Different region (cross-continent) | Different region | $0.08-0.15 | Use Cloud CDN, minimize cross-region |
| To internet | Internet | $0.12-0.23 | Use Cloud CDN, egress optimization |

### Optimization Strategies

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Zone affinity | 20-30% | Deploy workloads in same zone |
| Regional services | 10-20% | Use regional instead of zonal resources |
| Cloud CDN | 30-50% | Cache static content at edge |
| Compression | 20-40% | Enable gzip for HTTP responses |
| Data deduplication | 10-30% | Remove duplicate data transfers |

## Shared VPC Cost Benefits

### Cost Comparison

| Scenario | VPCs | NATs | Firewall Rules | Monthly Cost |
|----------|------|------|----------------|--------------|
| Standalone VPCs (5 projects) | 5 | 5 | 25 | $162 + data |
| Shared VPC (1 host + 4 service) | 1 | 1 | 5 | $32 + data |
| Savings | 80% | 80% | 80% | **80%** |

### Implementation

```bash
# Create shared NAT in host project
gcloud compute routers nats create "{{user.nat_name}}" \
  --project="{{user.host_project}}" \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --nat-all-subnet-ip-ranges \
  --auto-allocate-nat-external-ips
```

See [Shared VPC Setup](./shared-vpc-setup.md) for complete configuration.

## Cost Monitoring

### Budget Alerts

```bash
# Create budget alert for networking costs
gcloud billing budgets create \
  --billing-account="{{user.billing_account_id}}" \
  --display-name="VPC Network Budget" \
  --budget-amount=500USD \
  --threshold-rules=percent=0.5 \
  --filter-projects="projects/{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter-labels="service:networking"
```

### Cost Explorer Queries

```bash
# Query networking costs
gcloud billing accounts describe "{{user.billing_account_id}}" \
  --format="json" | \
  jq '.costBreakdown.network'

# List top-cost VPC resources
gcloud billing budgets list \
  --billing-account="{{user.billing_account_id}}"
```

### Monitoring Dashboard

```bash
# Create custom dashboard for VPC costs
gcloud monitoring dashboards create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --dashboard-json='{
    "displayName": "VPC Cost Dashboard",
    "gridLayout": {
      "widgets": [
        {
          "title": "NAT Gateway Costs",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "apiSource": "DEFAULT_CLOUD",
                "timeSeriesFilter": {
                  "filter": "metric.type=\"networking.googleapis.com/nat_gateway/cost\""
                }
              }
            }]
          }
        },
        {
          "title": "Data Transfer Costs",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "apiSource": "DEFAULT_CLOUD",
                "timeSeriesFilter": {
                  "filter": "metric.type=\"networking.googleapis.com/vpc/egress_bytes_count\""
                }
              }
            }]
          }
        }
      ]
    }
  }'
```

## Automated Cost Control

### Cloud Scheduler + Cloud Function

```yaml
# Schedule NAT cleanup for dev environment
# cron: 0 20 * * 5 (every Friday at 8 PM)
# Function: cleanup_dev_nat.py

import googleapiclient.discovery

def cleanup_dev_nat(event, context):
    compute = googleapiclient.discovery.build('compute', 'v1')
    
    # Delete NAT for dev environment
    compute.routers().delete(
        project="{{user.dev_project}}",
        region="us-central1",
        router="dev-router"
    ).execute()
    
    print("Dev NAT deleted for weekend cost savings")
```

### Terraform Budget Module

```hcl
resource "google_billing_budget" "network" {
  billing_account = "{{user.billing_account_id}}"
  display_name    = "VPC Network Budget"

  budget_filter {
    projects       = ["projects/{{env.CLOUDSDK_CORE_PROJECT}}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
    services        = ["compute.googleapis.com"]
    subaccounts     = []
    labels          = {
      service = "networking"
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "500"
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.8
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
```

## Troubleshooting High Costs

### Unexpected NAT Charges

**Diagnosis:**
```bash
# Check NAT gateway usage
gcloud compute routers nats describe "{{user.nat_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --format="json" | \
  jq '{name, natIpAllocateOption, minPortsPerVm, maxPortsPerVm}'

# Check if NAT is serving unused subnets
gcloud compute routers nats list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}"
```

**Solution:** Remove unused subnets from NAT configuration.

### Unexpected Data Transfer Charges

**Diagnosis:**
```bash
# Check data transfer volume by region
gcloud logging read \
  "resource.type=gce_instance AND jsonPayload.bytes_sent > 0" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=10
```

**Solution:** Enable Cloud CDN, compress data, or move workloads to same zone.

### Unexpected Static IP Charges

**Diagnosis:**
```bash
# List all static IPs and their status
gcloud compute addresses list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name, address, address_type, status)"
```

**Solution:** Delete unused static IPs:
```bash
gcloud compute addresses delete "{{user.unused_ip_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --quiet
```

## See Also

- [Google Cloud VPC Pricing](https://cloud.google.com/vpc/pricing)
- [Cloud NAT Pricing](https://cloud.google.com/nat/pricing)
- [VPN Pricing](https://cloud.google.com/vpn/pricing)
- [Data Transfer Pricing](https://cloud.google.com/vpc/network-pricing)
- [Shared VPC Setup](./shared-vpc-setup.md)
- [AIOps Anomaly Detection](./aiops-network-anomaly.md)