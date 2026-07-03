locals {
  bucket_names = tolist(var.bucket_names)
}
resource "google_service_account" "account" {
  account_id   = var.account_id
  display_name = var.display_name
}
resource "google_project_iam_member" "app_roles" {
  for_each = var.service_account_roles
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.account.email}"
}
resource "google_storage_bucket_iam_member" "bucket_access" {
  count  = length(local.bucket_names)
  bucket = local.bucket_names[count.index]
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.account.email}"
}
resource "google_service_account_key" "signed_url_key" {
  service_account_id = google_service_account.account.name
}
