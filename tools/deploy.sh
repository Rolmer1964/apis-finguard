#!/usr/bin/env bash
# Faz deploy de uma tag ja publicada (ver tools/publish_ecr.sh) na EC2:
# SSH na instancia, `docker compose pull` + `up -d` so dos servicos
# informados, com a tag pedida via IMAGE_TAG. Nao mexe em segredo nenhum -
# ANTHROPIC_API_KEY continua sendo buscado pelo proprio fin_triage/fin_risk
# no SSM Parameter Store, no boot deles.
#
# O "up -d" usa --no-deps: sem isso, o Compose inclui as dependencias por
# padrao (ex.: fin_web depende do fin_orchestrator, que depende das 7
# folhas), entao pedir so "fin_web" recriaria a cadeia inteira - ja
# aconteceu (deploy de fin_web recriou os 9 containers, sem necessidade).
# ("pull" ja e restrito por padrao - so ganha dependencias com
# --include-deps, que a gente NAO usa.)
#
# Uso:
#   bash tools/deploy.sh fin_triage fin_risk            # deploya o SHA do commit atual
#   bash tools/deploy.sh --tag 25f8108 fin_triage        # deploya uma tag especifica (rollback)
#   bash tools/deploy.sh --tag latest fin_web            # redeploya a tag latest (raro; prefira SHA)
#
# Requer no .env (raiz do projeto): DEPLOY_EC2_HOST, DEPLOY_EC2_USER,
# DEPLOY_EC2_KEY, ECR_REGISTRY.
#
# ATENCAO: este script so mexe em imagem/container. Se docker-compose.yml ou
# docker-compose.prod.yml mudaram (ex.: nova env var, novo servico), copie os
# dois pra instancia ANTES de rodar isto:
#   scp -i "$DEPLOY_EC2_KEY" docker-compose.yml docker-compose.prod.yml \
#       "${DEPLOY_EC2_USER}@${DEPLOY_EC2_HOST}:~/apis_finguard/"
# A instancia tem sua PROPRIA copia desses arquivos - editar so localmente
# nao propaga sozinho (ja aconteceu: IMAGE_TAG foi adicionado aqui sem
# sincronizar o .prod.yml remoto, e o deploy seguiu puxando ":latest" calado).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${DEPLOY_EC2_HOST:?defina DEPLOY_EC2_HOST no .env}"
: "${DEPLOY_EC2_USER:?defina DEPLOY_EC2_USER no .env}"
: "${DEPLOY_EC2_KEY:?defina DEPLOY_EC2_KEY no .env}"

TAG="$(git rev-parse --short HEAD)"
if [ "${1:-}" = "--tag" ]; then
  TAG="$2"
  shift 2
fi

if [ "$#" -eq 0 ]; then
  echo "Uso: bash tools/deploy.sh [--tag <sha|latest>] <servico...>" >&2
  echo "Ex.:  bash tools/deploy.sh fin_triage fin_risk" >&2
  exit 1
fi
SERVICES=("$@")

echo "== Deploy: ${SERVICES[*]} (tag ${TAG}) em ${DEPLOY_EC2_HOST} =="

ssh -i "$DEPLOY_EC2_KEY" "${DEPLOY_EC2_USER}@${DEPLOY_EC2_HOST}" "
  set -euo pipefail
  cd apis_finguard
  export IMAGE_TAG='${TAG}'
  docker compose -f docker-compose.yml -f docker-compose.prod.yml pull ${SERVICES[*]}
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ${SERVICES[*]}
  docker compose -f docker-compose.yml -f docker-compose.prod.yml ps ${SERVICES[*]}
"

echo ""
echo "Deploy feito: ${SERVICES[*]} -> tag ${TAG}"
