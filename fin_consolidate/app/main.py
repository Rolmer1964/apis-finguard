"""FinGuard - Consolidate API.

Serviço standalone (nó de consolidação do grafo do FinGuard) que expõe:
- POST /v1/consolidate  -> aplica as regras POL-SAC-001 sobre triagem + risco
- GET  /health          -> healthcheck

Lógica 100% determinística: não usa AWS nem chama outros serviços.
"""

import logging

from fastapi import FastAPI, Response

from .config import get_settings
from .logging_config import setup_logging
from .routers import consolidate, health

setup_logging()
logger = logging.getLogger("fin_consolidate.api")

_settings = get_settings()
logger.info("fin_consolidate iniciado (auth_por_api_key=%s)", bool(_settings.API_KEY))


app = FastAPI(
    title="FinGuard - Consolidate API",
    description=(
        "Serviço responsável por consolidar o resultado da triagem e da análise "
        "de risco aplicando as regras determinísticas da POL-SAC-001: SLA por "
        "urgência, área responsável por produto e overrides de canal regulatório "
        "(Banco Central / Procon / Justiça)."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(consolidate.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
