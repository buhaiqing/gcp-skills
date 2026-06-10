# environments/dev/outputs.tf
output "dev_db_connection_name" {
  description = "Cloud SQL dev instance connection name"
  value       = google_sql_database_instance.dev_db.connection_name
}

output "dev_vpc_network_id" {
  description = "Dev VPC network self-link"
  value       = google_compute_network.dev_vpc.id
}