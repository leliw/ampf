#!/bin/bash
ENVIRONMENT=${1:-dev}

INFRA_DIR=$(cd -- "$(dirname -- "$0")" &> /dev/null && pwd)
ENV_DIR="$INFRA_DIR/env/$ENVIRONMENT"
set -euo pipefail

terraform init \
    -backend-config="${ENV_DIR}/backend.hcl" \
    -reconfigure
terraform apply \
    -var="environment=${ENVIRONMENT}" \
    -var-file="${ENV_DIR}/terraform.tfvars"

if [ "$ENVIRONMENT" = "local" ] || [ "$ENVIRONMENT" = "it" ] || [ "$ENVIRONMENT" = "dev" ]; then
  mkdir -p ${ENV_DIR}
  terraform output --raw env_file > "${ENV_DIR}/.env.app"
  terraform output --raw service_account_key > "${ENV_DIR}/.gcp_credentials.json"
fi
