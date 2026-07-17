locals {
  enable_otel            = var.image_registry != null && var.image_registry != ""
}

resource "google_cloud_run_v2_service" "app" {
  name                 = var.name
  location             = var.region
  ingress              = var.public ? "INGRESS_TRAFFIC_ALL" : "INGRESS_TRAFFIC_INTERNAL_ONLY"
  invoker_iam_disabled = var.public
  deletion_protection  = var.deletion_protection

  # Terraform error - always detects changes if omitted
  scaling {
    min_instance_count = var.min_instances
  }

  template {
    service_account = var.service_account_email
    containers {
      name  = var.name
      image = var.container_image

      ports {
        container_port = var.container_port
      }
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      dynamic "env" {
        for_each = var.env_vars_plain

        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.enable_otel ? [1] : []
        content {
          name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
          value = "http://localhost:4318"
        }
      }
      dynamic "env" {
        for_each = var.env_vars_secrets
        content {
          name = env.key

          value_source {
            secret_key_ref {
              secret  = "projects/${var.project_id}/secrets/${env.value}"
              version = "latest"
            }
          }
        }
      }
    }
    # ==================== Sidecar otelcol ====================
    dynamic "containers" {
      for_each = local.enable_otel ? [1] : []
      content {
        name  = "otelcol"
        image = "${var.image_registry}/otelcol-gcp:0.135.6"

        resources {
          limits = {
            cpu    = "250m"
            memory = "512Mi"
          }
        }

        startup_probe {
          initial_delay_seconds = 10
          period_seconds        = 30
          timeout_seconds       = 1
          failure_threshold     = 3

          http_get {
            path = "/"
            port = 13133
          }
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
      }
    }
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].labels,
      template[0].annotations,
    ]
  }
}

resource "google_cloud_run_service_iam_member" "public" {
  count    = var.public ? 1 : 0
  project  = google_cloud_run_v2_service.app.project
  location = google_cloud_run_v2_service.app.location
  service  = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
