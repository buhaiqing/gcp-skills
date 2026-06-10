# environments/dev/terraform.tfvars
# Non-sensitive variables for dev environment
# Secrets (passwords, keys) must NOT be placed here — use GCP Secret Manager references

project_id = "dev-project-123456"
region     = "us-central1"