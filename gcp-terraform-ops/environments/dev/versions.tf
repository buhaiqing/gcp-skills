# environments/dev/versions.tf
# Terraform and provider version constraints
# Versions are pinned to prevent drift across environments

terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"  # Pinned: prevents unexpected provider upgrades
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}