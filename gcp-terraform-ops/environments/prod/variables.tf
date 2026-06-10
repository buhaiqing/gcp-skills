# environments/prod/variables.tf
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "us-central1"
}

variable "failover_region" {
  description = "Failover GCP region"
  type        = string
  default     = "us-east1"
}