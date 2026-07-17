variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
variable "service_id" {
  type = string
}
variable "custom_domain" {
  type = string
}


output "firebase_dns_records" {
  value       = try(google_firebase_hosting_custom_domain.custom_domain.required_dns_updates, null)
  description = "Rekordy DNS, które trzeba dodać u dostawcy domeny"
}


# Firebase Hosting Site
resource "google_firebase_hosting_site" "main" {
  provider = google-beta
  site_id  = var.service_id
  project  = var.project_id
}

# Custom Domain
resource "google_firebase_hosting_custom_domain" "custom_domain" {
  provider      = google-beta
  project       = var.project_id
  site_id       = google_firebase_hosting_site.main.site_id
  custom_domain = var.custom_domain

  # Opcjonalnie: automatyczne przekierowanie www → non-www lub odwrotnie
  # redirect_target = "..."
}

resource "google_firebase_hosting_version" "version" {
  provider = google-beta
  site_id  = google_firebase_hosting_site.main.site_id

  config {
    rewrites {
      glob = "/**"
      run {
        service_id = var.service_id
        region     = var.region
      }
    }
  }
}

# Release (to jest brakujący element!)
resource "google_firebase_hosting_release" "release" {
  provider     = google-beta
  site_id      = google_firebase_hosting_site.main.site_id
  version_name = google_firebase_hosting_version.version.name
  message      = "Deployment via Terraform"
}
