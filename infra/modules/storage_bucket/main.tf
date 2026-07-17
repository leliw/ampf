locals {
  bucket_name = "${var.name_prefix}-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 3
}

resource "google_storage_bucket" "bucket" {
  project                     = var.project_id
  name                        = local.bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  force_destroy               = var.environment != "prod"
  uniform_bucket_level_access = true

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age        = 90
      with_state = "ANY"
    }
  }
}
