# environments/dev/main.tf
# Dev environment — sample resources for demonstration
# DO NOT apply production workloads to dev environment

# Network foundation
resource "google_compute_network" "dev_vpc" {
  name                    = "dev-vpc-${var.project_id}"
  auto_create_subnetworks = false
  description             = "Dev environment VPC network"
}

resource "google_compute_subnetwork" "dev_subnet" {
  name          = "dev-subnet"
  network       = google_compute_network.dev_vpc.id
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
}

# Cloud SQL instance (dev — low tier)
resource "google_sql_database_instance" "dev_db" {
  name             = "dev-postgres-${var.project_id}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size        = 10
    ip_configuration {
      authorized_networks {
        name = "dev-office"
        value = "0.0.0.0/0"
      }
    }
  }

  deletion_protection = false  # Dev environment — allow delete without extra confirmation
}

resource "google_sql_database" "dev_database" {
  name     = "devapp"
  instance = google_sql_database_instance.dev_db.name
}

# Secret (example — secret value must NOT be in tfvars, use Secret Manager reference)
resource "google_secret_manager_secret" "dev_db_password" {
  secret_id = "dev-db-password"

  replication {
    auto {}
  }
}