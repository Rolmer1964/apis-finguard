#!/usr/bin/env bash
# Builda e publica imagens dos servicos apis_finguard no ECR.
#
# Cada imagem recebe DUAS tags: :latest (conveniencia) e :<sha> (o hash curto
# do commit git de onde o codigo veio). A tag :latest muda de significado a
# cada push; a tag :<sha> e fixa para sempre - "fin_triage:729950f" sempre vai
# significar exatamente o codigo daquele commit, permitindo rastrear o que
# esta rodando e fazer rollback trocando so a tag. Ver docs/DEPLOY_AWS.md.
#
# Uso:
#   bash tools/publish_ecr.sh                     # publica os 9 servicos
#   bash tools/publish_ecr.sh fin_triage fin_risk # publica so os informados
#
# Requer no .env (raiz do projeto): ECR_REGISTRY=<conta>.dkr.ecr.<regiao>.amazonaws.com
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${ECR_REGISTRY:?defina ECR_REGISTRY no .env (ex.: 123456789012.dkr.ecr.us-east-1.amazonaws.com)}"
REGION="us-east-1"
PROFILE="finguard-sso"
REPO_PREFIX="apis-finguard"
SHA="$(git rev-parse --short HEAD)"

ALL_SERVICES=(
  fin_guardrail
  fin_triage
  fin_rag
  fin_risk
  fin_consolidate
  fin_report_writer
  fin_traces
  fin_orchestrator
  fin_web
)

if [ "$#" -gt 0 ]; then
  SERVICES=("$@")
else
  SERVICES=("${ALL_SERVICES[@]}")
fi

echo "== login no ECR (${ECR_REGISTRY}) =="
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" \
  | podman login --username AWS --password-stdin "$ECR_REGISTRY"

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

  echo "== ${svc}: tag :latest e :${SHA} =="
  podman tag "${svc}:latest" "${ECR_REGISTRY}/${repo}:latest"
  podman tag "${svc}:latest" "${ECR_REGISTRY}/${repo}:${SHA}"

  echo "== ${svc}: push =="
  podman push "${ECR_REGISTRY}/${repo}:latest"
  podman push "${ECR_REGISTRY}/${repo}:${SHA}"

  echo "== ${svc}: OK (tags latest, ${SHA}) =="
done

echo ""
echo "Publicado: ${SERVICES[*]} (SHA ${SHA})"
