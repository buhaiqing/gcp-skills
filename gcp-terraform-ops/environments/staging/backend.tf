# environments/staging/backend.tf
# GCS backend with DynamoDB state lock
# Bucket: gs://tf-state-staging-<project>/terraform/
# Different bucket from dev/prod — directory isolation guarantees no state collision

terraform {
  backend "gcs" {
    bucket = "tf-state-staging-${var.project_id}-terraform"
    prefix = "environments/staging"
  }
}