variable "project_id" {
  type        = string
  description = "The ID of the Google Cloud project where the service account will be created."
}
variable "region" {
  type = string
}
variable "environment" {
  type = string
}
variable "name_prefix" {
  type = string
}
