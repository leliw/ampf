output "account_id" {
  value = var.account_id
}
output "email" {
  value = google_service_account.account.email
}
output "private_key" {
  value     = base64decode(google_service_account_key.signed_url_key.private_key)
  sensitive = true
}
