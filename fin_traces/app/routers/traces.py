"""Endpoints do log de execução e do painel decisório."""

import logging

from fastapi import APIRouter, Depends, status

from ..decisorio import build_decisorio_stats, recompose_from_results
from ..dependencies import verify_api_key
from ..models import (
    ClearResponse,
    RecomposeRequest,
    RecomposeResponse,
    StoreResponse,
    TraceEntry,
)
from ..trace_store import append_trace, clear_traces, get_traces
from ..traces_context import build_traces_context

logger = logging.getLogger("fin_traces.api")

router = APIRouter(prefix="/v1", tags=["traces"])


@router.post(
    "/traces",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    summary="Registra uma entrada no log de execução",
)
def post_trace(entry: TraceEntry) -> StoreResponse:
    count = append_trace(entry.model_dump())
    logger.info(
        "trace armazenado trace_id=%s blocked=%s urgency=%s risk=%s (total=%d)",
        entry.trace_id, entry.blocked, entry.urgency, entry.risk_level, count,
    )
    return StoreResponse(count=count)


@router.get("/traces", summary="Contexto completo do log (com barras/pills, p/ o fin_web)")
def list_traces() -> dict:
    return build_traces_context(get_traces())


@router.get("/traces/stats", summary="Só as estatísticas de timing do log (JSON puro)")
def traces_stats() -> dict:
    return build_traces_context(get_traces())["st"]


@router.get("/decisorio/stats", summary="Agregações do Painel Decisório")
def decisorio_stats() -> dict:
    return build_decisorio_stats(get_traces())


@router.post(
    "/traces/recompose",
    response_model=RecomposeResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Reconstrói o log a partir do results de um relatório batch",
)
def recompose(payload: RecomposeRequest) -> RecomposeResponse:
    n = recompose_from_results(payload.results)
    logger.info("traces: recomposição — %d entrada(s) injetada(s)", n)
    return RecomposeResponse(recomposed=n)


@router.delete(
    "/traces",
    response_model=ClearResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Limpa o log de execução",
)
def clear() -> ClearResponse:
    n = clear_traces()
    logger.info("traces: log limpo (%d entrada(s) removida(s))", n)
    return ClearResponse(cleared=n)
