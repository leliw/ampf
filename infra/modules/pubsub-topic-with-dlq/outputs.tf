output "topic_name" {
  value       = google_pubsub_topic.main.name
  description = "Nazwa głównego topicu"
}

output "subscription_name" {
  value       = google_pubsub_subscription.main.name
  description = "Nazwa głównej subskrypcji"
}

output "dlq_topic_name" {
  value       = var.create_dlq ? google_pubsub_topic.dlq[0].name : null
  description = "Nazwa DLQ topicu (jeśli włączony)"
}

output "dlq_subscription_name" {
  value       = var.create_dlq ? google_pubsub_subscription.dlq_inspect[0].name : null
  description = "Subskrypcja do inspekcji DLQ"
}
