"""FinGuard - Risk API.

Serviço standalone (nó de avaliação de risco do grafo do FinGuard) que expõe:
- POST /v1/risk  -> avalia o risco da reclamação via Claude Sonnet
- GET  /health   -> healthcheck

Bootstrap apenas: configuração de logging, validação das settings, probe
opcional de conectividade com o Bedrock, criação do app e registro dos
routers. A lógica do endpoint vive em `app/routers/risk.py`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from .bedrock_errors import BEDROCK_ERRORS, classify_bedrock_error
from .config import get_settings
from .logging_config import setup_logging
from .routers import health, risk
from .risk_service import RiskService

setup_logging()
logger = logging.getLogger("fin_risk.api")

_settings = get_settings()
logger.info(
    "Bedrock risco: modelo=%s regiao=%s probe_startup=%s auth_por_api_key=%s",
    _settings.BEDROCK_MODEL_RISK,
    _settings.AWS_REGION,
    _settings.PROBE_ON_STARTUP,
    bool(_settings.API_KEY),
)


def _probe_bedrock() -> None:
    """Faz uma chamada real de 1 token ao Bedrock no startup.

    Se o probe falhar, o startup é **abortado** com
    `RuntimeError: [CODIGO] mensagem`, onde CODIGO identifica a causa exata
    (ver `app/bedrock_errors.py`). Desligue com PROBE_ON_STARTUP=false.
    """
    settings = get_settings()
    try:
        RiskService(settings).ping()
    except BEDROCK_ERRORS as exc:
        codigo, mensagem = classify_bedrock_error(
            exc,
            resource=settings.BEDROCK_MODEL_RISK,
            region=settings.AWS_REGION,
            profile=settings.AWS_PROFILE,
        )
        logger.error("Startup abortado [%s]: %s", codigo, mensagem)
        raise RuntimeError(f"[{codigo}] {mensagem}") from exc
    logger.info("Conectividade com o Amazon Bedrock verificada — API pronta.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().PROBE_ON_STARTUP:
        _probe_bedrock()
    yield


app = FastAPI(
    title="FinGuard - Risk API",
    description=(
        "Serviço responsável por avaliar o risco de uma reclamação bancária via "
        "Amazon Bedrock (Claude Sonnet): nível de risco (Baixo/Médio/Alto/Crítico), "
        "justificativa citando a POL-SAC-001 e a lista de ações imediatas obrigatórias. "
        "O contexto da Política Interna chega pronto no corpo (`policy_context`); "
        "o serviço não chama o RAG."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(risk.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
