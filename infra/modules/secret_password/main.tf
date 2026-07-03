variable "id" {
  type = string
  description = "Secret Id"
}
variable "length" {
  type = number
  description = "Length of the generated secret"
  default = 32
}
variable "special" {
  type = bool
  description = "Whether to include special characters in the generated secret"
  default = true
}

variable "override_special" {
  type = string
  description = "Special characters to override in the generated secret"
  default = "!@#$%&*()-_=+[]{}<>"
}

output "name" {
    value = google_secret_manager_secret.secret.name
}

output "id" {
    value = google_secret_manager_secret.secret.secret_id
}
output "version" {
    value = google_secret_manager_secret_version.version.name
}


resource "random_password" "password" {
  length           = var.length
  special          = var.special
  override_special = var.override_special
}

resource "google_secret_manager_secret" "secret" {
  secret_id = var.id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "version" {
  secret      = google_secret_manager_secret.secret.id
  secret_data = random_password.password.result
}
