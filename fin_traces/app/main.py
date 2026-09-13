"""FinGuard - Traces API.

Serviço standalone que mantém o log de execução do pipeline e o painel
decisório:
- POST   /v1/traces             -> registra uma entrada no log
- GET    /v1/traces             -> contexto completo (barras/pills) p/ o fin_web
- GET    /v1/traces/stats       -> só as estatísticas de timing
- GET    /v1/decisorio/stats    -> agregações do painel decisório
- POST   /v1/traces/recompose   -> reconstrói o log a partir de um relatório
- DELETE /v1/traces             -> limpa o log
- GET    /health                -> healthcheck

Lógica 100% determinística: não usa AWS nem chama outros serviços. O deque é
opcionalmente persistido em disco (`TRACES_PERSIST_PATH`).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from .config import get_settings
from .logging_config import setup_logging
from .routers import health, traces
from .trace_store import configure_persistence

setup_logging()
logger = logging.getLogger("fin_traces.api")

_settings = get_settings()
logger.info(
    "fin_traces iniciado (persist=%s auth_por_api_key=%s)",
    _settings.TRACES_PERSIST_PATH or "off",
    bool(_settings.API_KEY),
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_persistence(get_settings().TRACES_PERSIST_PATH)
    yield


app = FastAPI(
    title="FinGuard - Traces API",
    description=(
        "Serviço responsável pelo log de execução do pipeline (deque em memória) "
        "e pelo painel decisório: matriz urgência×risco, agregações por canal, "
        "área e prazo, e estatísticas de latência."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(traces.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
