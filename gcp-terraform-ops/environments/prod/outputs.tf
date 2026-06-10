# environments/prod/outputs.tf
output "prod_db_connection_name" {
  description = "Cloud SQL prod instance private IP connection name"
  value       = google_sql_database_instance.prod_db.private_ip_address != "" ? google_sql_database_instance.prod_db.private_ip_address : google_sql_database_instance.prod_db.connection_name
}

output "prod_vpc_network_id" {
  description = "Prod VPC network self-link"
  value       = google_compute_network.prod_vpc.id
}

output "prod_db_deletion_protection" {
  description = "Whether deletion protection is enabled on the prod database"
  value       = google_sql_database_instance.prod_db.deletion_protection
}