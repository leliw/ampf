variable "project_id" {
  type = string
}
variable "region" {
  type    = string
}
variable "name" {
  type        = string
  description = "Service name"
}
variable "container_image" {
  type        = string
  description = "Container image"
}
variable "container_port" {
  type        = number
  description = "Container port"
  default     = 8080
}
variable "image_registry" {
  type        = string
  default     = null
  description = "Container image registry (required for otelcol sidecar)"
}
variable "service_account_email" {
  type        = string
}
variable "env_vars_plain" {
  type        = map(string)
  default     = {}
  description = "Environment variables - plain strings"
}
variable "env_vars_secrets" {
  type        = map(string)
  default     = {}
  description = "Environment variables - secrets from Secret Manager"
}
variable "public" {
  type    = bool
  default = false
}
variable "deletion_protection" {
  type    = bool
  default = false
}
variable "cpu_limit" {
  type    = string
  default = "0.5"
}
variable "memory_limit" {
  type    = string
  default = "512Mi"
}
variable "min_instances" {
  type    = number
  default = 0
}
variable "max_instances" {
  type    = number
  default = 10
}

