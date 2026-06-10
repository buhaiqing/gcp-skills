# environments/prod/terraform.tfvars
# PRODUCTION — verify target workspace before any terraform apply/destroy
# GCL required: all mutations must go through plan preview + Critic review

project_id     = "prod-project-345678"
region         = "us-central1"
failover_region = "us-east1"