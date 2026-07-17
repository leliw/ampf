output "url" {
  value       = try(google_cloud_run_v2_service.app.uri, null)
  description = "Cloud Run service URL"
}
output "name" {
  value       = try(google_cloud_run_v2_service.app.name, null)
  description = "Cloud Run service name"
}
output "id" {
  value       = try(google_cloud_run_v2_service.app.id, null)
  description = "Cloud Run service Id"
}
