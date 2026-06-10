# environments/prod/backend.tf
# GCS backend with DynamoDB state lock
# Bucket: gs://tf-state-prod-<project>/terraform/
# CRITICAL: Different bucket from dev/staging — directory isolation guarantees no state collision
# WARNING: All terraform apply/destroy operations in prod require GCL required review

terraform {
  backend "gcs" {
    bucket = "tf-state-prod-${var.project_id}-terraform"
    prefix = "environments/prod"
  }
}