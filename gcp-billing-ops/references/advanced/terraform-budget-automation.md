# Budget Automation with Terraform — Google Cloud Billing

> Provides DevOps and FinOps teams with Terraform-based automation for Google Cloud billing budgets, alerts, and spend governance.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Budget Resource Configuration](#budget-resource-configuration)
4. [Alert Thresholds](#alert-thresholds)
5. [Notification Channels](#notification-channels)
6. [Conditional Budgets](#conditional-budgets)
7. [Cost Estimation Integration](#cost-estimation-integration)
8. [State Management](#state-management)
9. [See Also](#see-also)

## Overview

Terraform's `google_billing_account_budget` and `google_billing_account_secondary_tenants_budget` resources enable programmatic budget management across billing accounts, projects, and services.

### Key Features

- Threshold-based alerts at custom percentages
- Project and service-level filtering
- Pub/Sub notification integration
- Automated spend governance

## Prerequisites

```bash
# Install Terraform >= 1.0
terraform version

# Authenticate
gcloud auth application-default login

# Enable billing APIs
gcloud services enable billing.googleapis.com cloudbilling.googleapis.com
```

## Budget Resource Configuration

### Basic Billing Account Budget

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "billing_account_id" {
  description = "Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX)"
  type        = string
}

variable "notification_email" {
  description = "Email for budget alerts"
  type        = string
}

# Notification channel
resource "google_billing_account_ava_smtp" "smtp" {
  name  = "budget-alerts"
  email_address = var.notification_email
}

# Budget for entire billing account
resource "google_billing_account_budget" "account_budget" {
  billing_account = var.billing_account_id
  display_name    = "monthly-budget-all-services"

  budget_filter {
    # Apply to all projects and services
    projects  = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = 10000
      nanos         = 0
    }
  }

  threshold_rules {
    threshold_percent = 0.5   # 50%
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.75  # 75%
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9   # 90%
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0   # 100%
    spend_basis       = "FORECASTED_SPEND"
  }
}
```

### Project-Level Budget

```hcl
# budget-per-project.tf
resource "google_billing_account_budget" "project_budgets" {
  for_each = toset([
    {
      project_id = "prod-environment"
      budget     = 5000
      alerts     = [0.5, 0.75, 0.9, 1.0]
    },
    {
      project_id = "dev-environment"
      budget     = 1000
      alerts     = [0.5, 0.75, 0.9, 1.0]
    },
    {
      project_id = "data-pipeline"
      budget     = 3000
      alerts     = [0.5, 0.75, 0.9, 1.0]
    }
  ])

  billing_account = var.billing_account_id
  display_name    = "budget-${each.value.project_id}"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = each.value.budget
    }
  }

  dynamic "threshold_rules" {
    for_each = each.value.alerts
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }
}
```

## Alert Thresholds

### Standard Threshold Configuration

| Threshold | Action | Purpose |
|-----------|--------|---------|
| 50% | Warning | Early awareness |
| 75% | Warning | Action needed |
| 90% | Critical | Immediate action |
| 100% | Critical | Spending exceeded |

### Forecast-based Alerts

```hcl
# Forecast-based threshold (predicts month-end spend)
resource "google_billing_account_budget" "forecast_budget" {
  billing_account = var.billing_account_id
  display_name    = "forecast-budget"

  budget_filter {
    projects  = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = 10000
    }
  }

  # Alert when forecasted spend exceeds budget
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
}
```

### Service-Specific Budget

```hcl
# Service-level budget
resource "google_billing_account_budget" "compute_budget" {
  billing_account = var.billing_account_id
  display_name    = "compute-engine-budget"

  budget_filter {
    projects  = ["projects/${var.project_id}"]
    services  = ["services/6F81-5424-09FA"]  # Compute Engine service ID
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = 3000
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }
}
```

## Notification Channels

### Pub/Sub Integration

```hcl
# Create Pub/Sub topic for budget alerts
resource "google_pubsub_topic" "budget_alerts" {
  name = "budget-alerts-topic"
}

# Grant billing account permission to publish
resource "google_billing_account_iam_member" "budget_publisher" {
  billing_account_id = var.billing_account_id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:$(google_pubsub_topic.budget_alerts.id)"
}

# Budget with Pub/Sub notification
resource "google_billing_account_budget" "pubsub_budget" {
  billing_account = var.billing_account_id
  display_name    = "pubsub-budget-alert"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = 5000
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  notifications {
    pubsub_topic = google_pubsub_topic.budget_alerts.id
  }
}
```

### Email-based Notifications

```hcl
# Email notification channel
resource "google_monitoring_notification_channel" "email" {
  display_name = "billing-team-email"
  type         = "email"

  labels = {
    email_address = "billing-team@company.com"
  }
}
```

## Conditional Budgets

### Environment-based Budgets

```hcl
# Conditional budget based on environment label
variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

resource "google_billing_account_budget" "env_budget" {
  billing_account = var.billing_account_id
  display_name    = "env-budget-${var.environment}"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.environment == "prod" ? 20000 : 5000
    }
  }

  threshold_rules {
    threshold_percent = 0.75
    spend_basis       = "CURRENT_SPEND"
  }
}
```

## Cost Estimation Integration

### Pre-deployment Cost Check

```bash
#!/bin/bash
# validate-budget.sh — Run before terraform apply

BUDGET=$(terraform output -raw monthly_budget 2>/dev/null || echo "10000")
ESTIMATED=$(terraform show -json | jq -r '.values.root_module.resources[] | select(.type == "google_compute_instance") | .values | (.count * .machine_specs.cost_per_hour) * 730' 2>/dev/null | awk '{sum+=$1} END {print sum}')

if [ "$ESTIMATED" -gt "$BUDGET" ]; then
  echo "ERROR: Estimated monthly cost ($${ESTIMATED}) exceeds budget ($${BUDGET})"
  exit 1
fi

echo "Budget check passed: estimated $${ESTIMATED} < budget $${BUDGET}"
```

### Cost Estimation in Terraform Plan

```hcl
# cost-estimation.tf
locals {
  monthly_compute_cost = sum([for vm in google_compute_instance.this : vm.monthly_cost_estimate])
}

output "monthly_cost_estimate" {
  value = local.monthly_compute_cost
}

output "budget_headroom" {
  value = var.monthly_budget - local.monthly_compute_cost
}
```

## State Management

### Remote State Configuration

```hcl
# backend.tf
terraform {
  backend "gcs" {
    bucket = "tf-state-bucket"
    prefix = "billing-budgets"
  }
}
```

### State Import (Existing Budgets)

```bash
# Import existing budget to Terraform state
terraform import \
  google_billing_account_budget.account_budget \
  billingAccounts/XXXXXX-XXXXXX-XXXXXX/budgets/budget-0

# Verify import
terraform state list | grep budget
```

## See Also

- [FinOps Cost Analysis](finops-cost-analysis.md)
- [Google Cloud Budgets Terraform Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/billing_account_budget)
- [Google Cloud Budgets Documentation](https://cloud.google.com/cost-management/docs/how-to/budgets)
