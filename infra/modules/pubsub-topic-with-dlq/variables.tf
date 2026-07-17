variable "project_id" {
  type        = string
  description = "ID projektu GCP"
}

variable "region" {
  type        = string
  default     = "europe-west1"
  description = "Region (głównie dla IAM i ewentualnych future features)"
}

variable "topic_name" {
  type        = string
  description = "Nazwa głównego topicu"
}

variable "environment" {
  type        = string
  description = "dev / stg / prod – dodawane do nazw"
}

variable "create_dlq" {
  type        = bool
  default     = true
  description = "Czy tworzyć DLQ i powiązać z subskrypcją?"
}

variable "max_delivery_attempts" {
  type        = number
  default     = 5
  description = "Ile razy Pub/Sub próbuje dostarczyć wiadomość zanim trafi do DLQ"
}

variable "ack_deadline_seconds" {
  type    = number
  default = 600   # 10 minut – bezpieczna wartość dla Cloud Run
}

variable "message_retention_duration" {
  type    = string
  default = "21600s"   # 6 godzin
  description = "Czas przechowywania wiadomości w subskrypcji"
}

variable "subscription_name_suffix" {
  type    = string
  default = "sub"
  description = "Sufiks nazwy subskrypcji (np. sub, worker, push)"
}

variable "push_endpoint" {
  type    = string
  default = null
  description = "Jeśli podasz → tworzy PUSH subscription. Format: https://..."
}

variable "push_service_account_email" {
  type    = string
  default = null
  description = "Service Account używany do autoryzacji push (OIDC token)"
}

variable "labels" {
  type    = map(string)
  default = {}
  description = "Dodatkowe labelki"
}
