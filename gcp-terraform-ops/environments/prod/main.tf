# environments/prod/main.tf
# Production environment — full HA, deletion protection enabled
# GCL required for all terraform apply and terraform destroy operations

resource "google_compute_network" "prod_vpc" {
  name                    = "prod-vpc-${var.project_id}"
  auto_create_subnetworks = false
  description             = "Production environment VPC network — HA multi-region"
}

resource "google_compute_subnetwork" "prod_subnet_primary" {
  name          = "prod-subnet-primary"
  network       = google_compute_network.prod_vpc.id
  ip_cidr_range = "10.30.0.0/24"
  region        = var.region
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "prod_subnet_secondary" {
  name          = "prod-subnet-secondary"
  network       = google_compute_network.prod_vpc.id
  ip_cidr_range = "10.31.0.0/24"
  region        = var.failover_region
  private_ip_google_access = true
}

# Cloud SQL instance (prod — high tier, HA, deletion protection)
resource "google_sql_database_instance" "prod_db" {
  name             = "prod-postgres-${var.project_id}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-n1-standard-8"
    availability_type = "REGIONAL"  # Multi-zone HA
    disk_size        = 200
    disk_type        = "PD_SSD"
    ip_configuration {
      private_network = google_compute_network.prod_vpc.id
      # No public IP — private network only
      ipv4_enabled    = false
    }
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
    }
  }

  deletion_protection = true  # PROD — blocks terraform destroy without explicit flag
}

resource "google_sql_database" "prod_database" {
  name     = "prodapp"
  instance = google_sql_database_instance.prod_db.name
}

# VPC Service Controls perimeter membership (example)
data "google_project" "prod" {
  project_id = var.project_id
}