output "bucket_name" {
  value = module.bucket.name
}
output "service_account_key" {
  value       = module.service_account.private_key
  description = "Cloud Run service account private key"
  sensitive   = true
}
output "env_file" {
  value = join("\n", concat(
    [
      for key, val in local.env_vars_plain :
      "${key}=\"${val}\""
      if val != null
    ],
    [""]
  ))
}