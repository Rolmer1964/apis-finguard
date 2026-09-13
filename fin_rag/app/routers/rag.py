"""Endpoints de RAG: retrieval, ingestão, stats e reset do índice."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from ..config import Settings, get_settings
from ..dependencies import get_rag_service, verify_api_key
from ..index_state import get_ingest_state
from ..models import (
    ChunkOut,
    IngestStartResponse,
    IngestStatusResponse,
    ResetResponse,
    RetrieveRequest,
    RetrieveResponse,
    StatsResponse,
)
from ..rag_service import RagService

logger = logging.getLogger("fin_rag.api")

router = APIRouter(prefix="/v1/rag", tags=["rag"])


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Busca os top-k trechos mais relevantes da Política Interna",
)
def retrieve(
    payload: RetrieveRequest,
    service: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> RetrieveResponse:
    try:
        chunks, policy_context = service.retrieve(payload.query, payload.k)
    except Exception as exc:
        logger.exception("Falha ao gerar embedding para retrieval")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"codigo": "EMBED_MODEL_ERRO", "mensagem": str(exc)},
        ) from exc
    logger.info("retrieve k=%s -> %d trechos", payload.k or settings.RAG_TOP_K, len(chunks))
    return RetrieveResponse(
        chunks=[ChunkOut(text=c.text, source=c.source, chunk_idx=c.chunk_idx, score=c.score) for c in chunks],
        count=len(chunks),
        policy_context=policy_context,
    )


@router.post(
    "/ingest",
    response_model=IngestStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
    summary="Dispara a ingestão incremental da Política Interna em background",
)
def ingest(
    background_tasks: BackgroundTasks,
    service: RagService = Depends(get_rag_service),
) -> IngestStartResponse:
    if get_ingest_state()["status"] == "running":
        return IngestStartResponse(status="already_running")
    background_tasks.add_task(service.run_ingest_bg)
    return IngestStartResponse(status="started")


@router.get(
    "/ingest/status",
    response_model=IngestStatusResponse,
    summary="Estado da última/atual ingestão",
)
def ingest_status() -> IngestStatusResponse:
    return IngestStatusResponse(**get_ingest_state())


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Resumo do índice: total de vetores, arquivos e data da última ingestão",
)
def stats(service: RagService = Depends(get_rag_service)) -> StatsResponse:
    return StatsResponse(**service.stats())


@router.post(
    "/reset",
    response_model=ResetResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Apaga os arquivos do índice (regenerável via /ingest)",
)
def reset(service: RagService = Depends(get_rag_service)) -> ResetResponse:
    return ResetResponse(**service.reset())
