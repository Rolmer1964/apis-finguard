"""FinGuard - Report Writer API.

Serviço standalone que gera e serve o relatório gerencial do FinGuard:
- POST   /v1/reports                       -> gera JSON/CSV/MD de um batch
- GET    /v1/reports                       -> lista os relatórios
- GET    /v1/reports/{stem}                -> contexto agregado (JSON)
- GET    /v1/reports/{stem}/html           -> HTML renderizado
- GET    /v1/reports/{stem}/record/{id}    -> registro completo por id
- DELETE /v1/reports/{stem}                -> remove os artefatos
- GET    /output/{filename}                -> serve o artefato bruto
- GET    /health                           -> healthcheck

Lógica 100% determinística: não usa AWS nem chama outros serviços.
"""

import logging

from fastapi import FastAPI, Response

from .config import get_settings
from .logging_config import setup_logging
from .routers import health, reports

setup_logging()
logger = logging.getLogger("fin_report_writer.api")

_settings = get_settings()
logger.info(
    "fin_report_writer iniciado (output_dir=%s auth_por_api_key=%s)",
    _settings.OUTPUT_DIR,
    bool(_settings.API_KEY),
)


app = FastAPI(
    title="FinGuard - Report Writer API",
    description=(
        "Serviço responsável por gerar o relatório gerencial (JSON + CSV + "
        "Markdown + HTML com Chart.js) a partir de uma lista de registros "
        "processados, agregar distribuições e recomendações, e servir/armazenar "
        "os artefatos."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(reports.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
