"""FinGuard - Triage API.

Serviço standalone (nó de triagem do grafo do FinGuard) que expõe:
- POST /v1/triage  -> classifica a reclamação via Claude Haiku
- GET  /health     -> healthcheck

Bootstrap apenas: configuração de logging, validação das settings, probe
opcional de conectividade com o Bedrock, criação do app e registro dos
routers. A lógica do endpoint vive em `app/routers/triage.py`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from .bedrock_errors import BEDROCK_ERRORS, classify_bedrock_error
from .config import get_settings
from .logging_config import setup_logging
from .routers import health, triage
from .triage_service import TriageService

setup_logging()
logger = logging.getLogger("fin_triage.api")

_settings = get_settings()
logger.info(
    "Bedrock triagem: modelo=%s regiao=%s probe_startup=%s auth_por_api_key=%s",
    _settings.BEDROCK_MODEL_TRIAGE,
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
        TriageService(settings).ping()
    except BEDROCK_ERRORS as exc:
        codigo, mensagem = classify_bedrock_error(
            exc,
            resource=settings.BEDROCK_MODEL_TRIAGE,
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
    title="FinGuard - Triage API",
    description=(
        "Serviço responsável por classificar reclamações bancárias via Amazon "
        "Bedrock (Claude Haiku): categoria, produto, sentimento, urgência e um "
        "resumo neutro, aplicando os gatilhos de urgência da POL-SAC-001."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(triage.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
