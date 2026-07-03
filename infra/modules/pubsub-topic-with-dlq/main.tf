locals {
  topic_full_name        = var.topic_name
  dlq_topic_name         = "${local.topic_full_name}-dlq"
  subscription_full_name = "${local.topic_full_name}-${var.subscription_name_suffix}"
  dlq_subscription_name  = "${local.dlq_topic_name}-sub"

  effective_labels = merge(
    {
      environment = var.environment
      managed_by  = "terraform"
      component   = "pubsub"
    },
    var.labels
  )
}

# Główny topic
resource "google_pubsub_topic" "main" {
  project = var.project_id
  name    = local.topic_full_name
  labels  = local.effective_labels
}

# Dead Letter Topic (opcjonalny)
resource "google_pubsub_topic" "dlq" {
  count   = var.create_dlq ? 1 : 0
  project = var.project_id
  name    = local.dlq_topic_name
  labels  = merge(local.effective_labels, { purpose = "dead-letter" })
}

# Główna subskrypcja (pull lub push)
resource "google_pubsub_subscription" "main" {
  project = var.project_id
  name    = local.subscription_full_name
  topic   = google_pubsub_topic.main.id

  ack_deadline_seconds       = var.ack_deadline_seconds
  message_retention_duration = var.message_retention_duration
  labels                     = local.effective_labels

  dynamic "push_config" {
    for_each = var.push_endpoint != null ? [1] : []
    content {
      push_endpoint = var.push_endpoint

      dynamic "oidc_token" {
        for_each = var.push_service_account_email != null ? [1] : []
        content {
          service_account_email = var.push_service_account_email
        }
      }
    }
  }
  dynamic "dead_letter_policy" {
    for_each = var.create_dlq ? [1] : []
    content {
      dead_letter_topic     = google_pubsub_topic.dlq[0].id
      max_delivery_attempts = var.max_delivery_attempts
    }
  }
  # Retry policy – możesz dodać dynamicznie jeśli chcesz custom backoff
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Opcjonalna subskrypcja pull na DLQ – do ręcznego debugowania / replay
resource "google_pubsub_subscription" "dlq_inspect" {
  count   = var.create_dlq ? 1 : 0
  project = var.project_id
  name    = local.dlq_subscription_name
  topic   = google_pubsub_topic.dlq[0].id
  labels  = merge(local.effective_labels, { purpose = "dlq-inspect" })
}

# IAM – Pub/Sub service agent musi móc publikować do DLQ
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  count   = var.create_dlq ? 1 : 0
  project = var.project_id
  topic   = google_pubsub_topic.dlq[0].name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}


resource "time_sleep" "pubsub_sub_wait" {
  create_duration = "12s"
  depends_on      = [google_pubsub_subscription.main]
}

resource "google_pubsub_subscription_iam_member" "subscriber" {
  project      = var.project_id
  subscription = local.subscription_full_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [time_sleep.pubsub_sub_wait]
}

# Data source do pobrania project number (potrzebne do IAM)
data "google_project" "current" {
}
