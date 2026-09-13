"""FinGuard - Orchestrator API.

Ponto único de entrada: pipeline (`/analyze`, `/analyze-form`, `/batch`) +
proxies finos de leitura para o `fin_web`.
- GET /health             -> healthcheck local
- GET /health/downstream  -> pinga o /health de cada folha

Bootstrap apenas: logging, settings, app, routers. Sem AWS direto.
"""

import logging

from fastapi import FastAPI, Response

from .config import get_settings
from .logging_config import setup_logging
from .routers import analyze, health, proxy

setup_logging()
logger = logging.getLogger("fin_orchestrator.api")

_s = get_settings()
logger.info(
    "fin_orchestrator iniciado | guardrail=%s triage=%s rag=%s risk=%s consolidate=%s "
    "report_writer=%s traces=%s | auth_por_api_key=%s",
    _s.GUARDRAIL_URL, _s.TRIAGE_URL, _s.RAG_URL, _s.RISK_URL, _s.CONSOLIDATE_URL,
    _s.REPORT_WRITER_URL, _s.TRACES_URL, bool(_s.API_KEY),
)


app = FastAPI(
    title="FinGuard - Orchestrator API",
    description=(
        "Ponto único de entrada do FinGuard: reproduz o pipeline fim-a-fim "
        "(guardrail → triagem → RAG → risco → consolidação → guardrail → log) e "
        "o batch com controle adaptativo (AIMD), orquestrando as folhas por "
        "HTTP; e expõe proxies finos de leitura para a interface."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(proxy.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
