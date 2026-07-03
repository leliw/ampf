#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-dev}

INFRA_DIR=$(cd -- "$(dirname -- "$0")" &> /dev/null && pwd)
ENV_DIR="$INFRA_DIR/env/$ENVIRONMENT"

terraform init \
    -backend-config="${ENV_DIR}/backend.hcl" \
    -reconfigure
terraform destroy \
    -var="environment=${ENVIRONMENT}" \
    -var-file="${ENV_DIR}/terraform.tfvars"
