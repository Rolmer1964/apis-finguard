#!/usr/bin/env bash
# Publica as 8 imagens restantes no ECR (fin_rag ja foi feito em 2026-09-11).
# Uso: bash publish_ecr.sh
set -euo pipefail

ACCOUNT_ID="<SEU_ACCOUNT_ID>"
REGION="us-east-1"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
PROFILE="finguard-sso"
REPO_PREFIX="apis-finguard"

SERVICES=(
  fin_guardrail
  fin_triage
  fin_risk
  fin_consolidate
  fin_report_writer
  fin_traces
  fin_orchestrator
  fin_web
)

cd "$(dirname "$0")"
cd "/c/Users/Rolmer/local/pocs/apis_finguard"

echo "== login no ECR =="
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" \
  | podman login --username AWS --password-stdin "$REGISTRY"

for svc in "${SERVICES[@]}"; do
  repo="${REPO_PREFIX}/${svc}"
  echo ""
  echo "== ${svc}: create-repository (idempotente) =="
  aws ecr describe-repositories --region "$REGION" --profile "$PROFILE" \
    --repository-names "$repo" >/dev/null 2>&1 \
    || aws ecr create-repository --region "$REGION" --profile "$PROFILE" \
         --repository-name "$repo" \
         --image-scanning-configuration scanOnPush=true \
         --tags Key=project,Value=apis_finguard

  echo "== ${svc}: build =="
  podman build -t "${svc}:latest" "./${svc}"

  echo "== ${svc}: tag =="
  podman tag "${svc}:latest" "${REGISTRY}/${repo}:latest"

  echo "== ${svc}: push =="
  podman push "${REGISTRY}/${repo}:latest"

  echo "== ${svc}: OK =="
done

echo ""
echo "Todas as imagens publicadas."
