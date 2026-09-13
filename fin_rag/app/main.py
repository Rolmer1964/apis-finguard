"""FinGuard - RAG API.

Serviço standalone (nó de RAG do grafo do FinGuard) que expõe:
- POST /v1/rag/retrieve      -> top-k trechos da Política Interna + policy_context
- POST /v1/rag/ingest        -> re-ingestão incremental em background
- GET  /v1/rag/ingest/status -> estado da ingestão
- GET  /v1/rag/stats         -> resumo do índice
- POST /v1/rag/reset         -> apaga o índice (regenerável)
- GET  /health               -> healthcheck

Bootstrap: logging, settings, probe opcional do modelo de embedding local,
ingestão opcional em background, criação do app e routers.
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from .config import get_settings
from .logging_config import setup_logging
from .rag_service import RagService
from .routers import health, rag

setup_logging()
logger = logging.getLogger("fin_rag.api")

_settings = get_settings()
logger.info(
    "RAG: embed=%s dim=%d docs=%s index=%s probe=%s ingest_startup=%s",
    _settings.EMBED_MODEL_NAME, _settings.EMBED_DIM,
    _settings.RAG_DOCS_DIR, _settings.RAG_INDEX_DIR,
    _settings.PROBE_ON_STARTUP, _settings.INGEST_ON_STARTUP,
)


def _probe_embedder() -> None:
    """1 embedding local no startup; aborta com `RuntimeError` se o modelo não carregar."""
    settings = get_settings()
    try:
        RagService(settings).ping()
    except Exception as exc:
        logger.error(
            "Startup abortado: falha ao carregar o modelo de embedding local '%s': %s",
            settings.EMBED_MODEL_NAME, exc,
        )
        raise RuntimeError(
            f"[EMBED_MODEL_ERRO] Falha ao carregar o modelo de embedding local "
            f"'{settings.EMBED_MODEL_NAME}': {exc}"
        ) from exc
    logger.info("Modelo de embedding local carregado — API pronta.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.PROBE_ON_STARTUP:
        _probe_embedder()
    if settings.INGEST_ON_STARTUP:
        threading.Thread(
            target=lambda: RagService(get_settings()).run_ingest_bg(),
            daemon=True,
            name="rag-startup-ingest",
        ).start()
    yield


app = FastAPI(
    title="FinGuard - RAG API",
    description=(
        "Serviço responsável por indexar a Política Interna (FAISS + embeddings "
        "locais) e devolver os trechos mais relevantes para uma consulta, "
        "formatados como policy_context para o agente de risco."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(rag.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
