# environments/dev/backend.tf
# GCS backend with DynamoDB state lock
# Bucket: gs://tf-state-dev-<project>/terraform/
# Isolation: separate bucket from staging/prod to prevent cross-environment state corruption

terraform {
  backend "gcs" {
    bucket = "tf-state-dev-${var.project_id}-terraform"
    prefix = "environments/dev"
    # DynamoDB lock table for concurrent operation safety
    # Table: terraform-state-lock-dev (created separately)
    encryption_key = ""  # Add KMS key ARN if customer-managed encryption required
  }
}