"""FinGuard — Web UI (fin_web).

SSR das telas do FinGuard (formulário individual, lote, relatórios, log de
execução, painel decisório, admin, ADR, relatório técnico). Depende **só** do
`fin_orchestrator` — não conhece o endereço de nenhuma folha e não usa AWS.

Bootstrap apenas: logging, settings, app, static, routers.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .logging_config import setup_logging
from .routers import actions, health, pages

setup_logging()
logger = logging.getLogger("fin_web.api")

_s = get_settings()
logger.info("fin_web iniciado | orchestrator=%s | auth_por_api_key=%s",
            _s.orch, bool(_s.API_KEY))

_ASSETS = Path(__file__).parent / "assets"

app = FastAPI(
    title="FinGuard - Web UI",
    description=(
        "Interface HTML server-side do FinGuard. Consome exclusivamente o "
        "fin_orchestrator (pipeline + proxies de leitura)."
    ),
    version="1.0.0",
)

app.mount("/assets/images", StaticFiles(directory=str(_ASSETS / "images"), check_dir=False), name="images")
app.mount("/assets/presentation", StaticFiles(directory=str(_ASSETS / "presentation"), check_dir=False), name="presentation")

app.include_router(health.router)
app.include_router(pages.router)
app.include_router(actions.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
