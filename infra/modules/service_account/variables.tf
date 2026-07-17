variable "project_id" {
  type = string
  description = "The ID of the Google Cloud project where the service account will be created."
}
variable "account_id" {
  type = string
  description = "The unique identifier for the service account (the part before the @ symbol)."
}
variable "display_name" {
  type = string
  description = "The human-readable name for the service account as shown in the GCP Console."
}
variable "service_account_roles" {
  type = set(string)
  description = "A set of IAM roles to be granted to the service account at the project level, e.g., [\"roles/run.invoker\",\"roles/datastore.user\",\"roles/storage.objectUser\",\"roles/pubsub.publisher\",\"roles/pubsub.subscriber\",\"roles/iam.serviceAccountTokenCreator\"]"
}
variable "bucket_names" {
  type    = set(string)
  default = []
  description = "A set of Cloud Storage bucket names where the service account will be granted object user access."
}
