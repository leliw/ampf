locals {
  app_name = "ampf"

  name_prefix = "${var.environment}-${local.app_name}"

  service_account_name         = "${local.name_prefix}-sa"
  service_account_display_name = "Service Account for Cloud Run - ${local.name_prefix}"
  service_account_roles = [
    "roles/datastore.user",

    "roles/storage.objectUser",
    "roles/iam.serviceAccountTokenCreator",

    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
  ]
  env_vars_plain = {
    PROJECT_ID       = var.project_id
    GCP_BUCKET_NAME  = module.bucket.name
    GCP_DATABASE_1   = resource.google_firestore_database.firestore_1.name
    GCP_DATABASE_2   = resource.google_firestore_database.firestore_2.name
  }
}

module "bucket" {
  source      = "./modules/storage_bucket"
  project_id  = var.project_id
  name_prefix = local.name_prefix
  region      = var.region
  environment = var.environment
}

resource "google_firestore_database" "firestore_1" {
  project     = var.project_id
  name        = "${local.name_prefix}-1"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

resource "google_firestore_database" "firestore_2" {
  project     = var.project_id
  name        = "${local.name_prefix}-2"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

module "service_account" {
  source = "./modules/service_account"

  project_id            = var.project_id
  account_id            = local.service_account_name
  display_name          = local.service_account_display_name
  service_account_roles = local.service_account_roles
  bucket_names          = [module.bucket.name]
}
