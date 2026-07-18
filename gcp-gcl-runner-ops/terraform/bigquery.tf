# Terraform configuration for GCL BigQuery resources
# Version: 1.0.0
# Updated: 2026-07-18

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variable definitions
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "gcp_skills_gcl_audit"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

# BigQuery Dataset
resource "google_bigquery_dataset" "gcl_audit" {
  dataset_id    = var.dataset_id
  friendly_name = "GCL Audit Traces"
  description   = "GCL Generator-Critic-Loop execution traces for observability and analytics"
  location      = "US" # Consider making this configurable
  project       = var.project_id

  default_table_expiration_ms = 365 * 24 * 60 * 60 * 1000 # 1 year

  labels = {
    environment = var.environment
    team        = "platform"
    product     = "gcp-skills"
    managed_by  = "terraform"
  }

  access {
    role          = "roles/bigquery.dataEditor"
    special_group = "projectWriters"
  }

  access {
    role          = "roles/bigquery.dataViewer"
    special_group = "projectReaders"
  }
}

# BigQuery Table: gcl_traces
resource "google_bigquery_table" "gcl_traces" {
  dataset_id = google_bigquery_dataset.gcl_audit.dataset_id
  table_id   = "gcl_traces"
  project    = var.project_id

  deletion_protection = true # Prevent accidental deletion

  labels = {
    environment = var.environment
    team        = "platform"
    product     = "gcp-skills"
    version     = "1.0.0"
  }

  # Time partitioning
  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  # Clustering
  clustering = ["skill", "op", "result"]

  schema = file("${path.module}/../schema/gcl_traces_schema.json")

  # expiration = 365 * 24 * 60 * 60 * 1000  # Table-level expiration (optional)
}

# BigQuery Table: gcl_iterations (normalized iteration data)
resource "google_bigquery_table" "gcl_iterations" {
  dataset_id = google_bigquery_dataset.gcl_audit.dataset_id
  table_id   = "gcl_iterations"
  project    = var.project_id

  deletion_protection = true

  labels = {
    environment = var.environment
    team        = "platform"
    product     = "gcp-skills"
    version     = "1.0.0"
  }

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  clustering = ["skill", "op", "verdict"]

  schema = <<EOF
[
  {"name": "trace_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "iteration", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "skill", "type": "STRING", "mode": "REQUIRED"},
  {"name": "op", "type": "STRING", "mode": "REQUIRED"},
  {"name": "result", "type": "STRING", "mode": "NULLABLE"},
  {"name": "exit_code", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "verdict", "type": "STRING", "mode": "NULLABLE"},
  {"name": "latency_ms", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "safety_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "correctness_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "idempotency_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "highest_risk", "type": "STRING", "mode": "NULLABLE"},
  {"name": "error_type", "type": "STRING", "mode": "NULLABLE"}
]
EOF
}

# IAM for service account (if using service account authentication)
data "google_service_account" "gcl_runner_sa" {
  count      = var.environment == "production" ? 1 : 0
  account_id = "gcl-runner@${var.project_id}.iam"
}

resource "google_bigquery_dataset_iam_member" "gcl_audit_editor" {
  count      = var.environment == "production" ? 1 : 0
  dataset_id = google_bigquery_dataset.gcl_audit.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${data.google_service_account.gcl_runner_sa[0].email}"
}

resource "google_bigquery_dataset_iam_member" "gcl_audit_viewer" {
  count      = var.environment == "production" ? 1 : 0
  dataset_id = google_bigquery_dataset.gcl_audit.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${data.google_service_account.gcl_runner_sa[0].email}"
}

# Outputs
output "dataset_id" {
  value = google_bigquery_dataset.gcl_audit.dataset_id
}

output "table_id" {
  value = google_bigquery_table.gcl_traces.table_id
}

output "dataset_uri" {
  value = "bq://${var.project_id}.${google_bigquery_dataset.gcl_audit.dataset_id}"
}
