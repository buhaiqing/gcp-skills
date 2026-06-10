# environments/staging/main.tf
# Staging environment — mirrors production topology at reduced scale

resource "google_compute_network" "staging_vpc" {
  name                    = "staging-vpc-${var.project_id}"
  auto_create_subnetworks = false
  description             = "Staging environment VPC network"
}

resource "google_compute_subnetwork" "staging_subnet" {
  name          = "staging-subnet"
  network       = google_compute_network.staging_vpc.id
  ip_cidr_range = "10.20.0.0/24"
  region        = var.region
}

# Cloud SQL instance (staging — medium tier, HA)
resource "google_sql_database_instance" "staging_db" {
  name             = "staging-postgres-${var.project_id}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-n1-standard-2"
    availability_type = "REGIONAL"  # HA for staging
    disk_size        = 50
    ip_configuration {
      authorized_networks {
        name = "internal"
        value = "10.0.0.0/8"
      }
    }
  }

  deletion_protection = true  # Staging — protect against accidental delete
}