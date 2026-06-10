# environments/staging/outputs.tf
output "staging_db_connection_name" {
  description = "Cloud SQL staging instance connection name"
  value       = google_sql_database_instance.staging_db.connection_name
}