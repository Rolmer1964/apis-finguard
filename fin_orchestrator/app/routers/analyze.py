"""Rotas do pipeline: /analyze, /analyze-form, /batch."""

import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .. import batch as batch_mod
from .. import clients
from ..dependencies import verify_api_key
from ..models import AnalyzeRequest
from ..pipeline import analyze_one, blocked_record

logger = logging.getLogger("fin_orchestrator.api")

router = APIRouter(tags=["pipeline"], dependencies=[Depends(verify_api_key)])


def _downstream_http_error(exc: clients.DownstreamError) -> HTTPException:
    """Propaga a falha de uma folha como 502, preservando o `detail` original."""
    return HTTPException(
        status_code=502,
        detail={"service": exc.service, "downstream_status": exc.status_code, "erro": exc.detail},
    )


@router.post("/analyze", summary="Roda o pipeline completo numa reclamação")
def analyze(payload: AnalyzeRequest) -> JSONResponse:
    try:
        result = analyze_one(payload.text, payload.product_hint, canal=payload.canal)
    except clients.DownstreamError as exc:
        logger.error("pipeline abortado: %s", exc)
        raise _downstream_http_error(exc) from exc
    return JSONResponse(result)


@router.post("/analyze-form", summary="Como /analyze, mas via form e persistindo um relatório unitário")
def analyze_form(
    text: str = Form(...),
    product_hint: str = Form(""),
    canal: str = Form("Web"),
) -> JSONResponse:
    canal_val = canal.strip() or "Web"
    try:
        result = analyze_one(text, product_hint or None, canal=canal_val)
        rec_id = result.get("trace_id")
        if result.get("blocked"):
            record = blocked_record(rec_id, canal_val, result)
        else:
            record = {"id": rec_id, "canal": canal_val, **result}
        report = clients.create_report([record], {"label": "Consulta unitária"})
    except clients.DownstreamError as exc:
        logger.error("analyze-form abortado: %s", exc)
        raise _downstream_http_error(exc) from exc
    return JSONResponse({"stem": report["stem"], "paths": report["paths"], "result": result})


@router.post("/batch", summary="Processa um CSV em lote (AIMD) e gera o relatório")
async def batch(file: UploadFile = File(...), label: str = Form("")) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Envie um arquivo .csv")
    raw = (await file.read()).decode("utf-8", errors="replace")
    try:
        rows = batch_mod.parse_csv(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not rows:
        raise HTTPException(400, "CSV sem linhas úteis (coluna 'texto_reclamacao' vazia?)")

    try:
        summary = await asyncio.to_thread(batch_mod.run_batch, rows, label or None, file.filename)
    except clients.DownstreamError as exc:
        logger.error("batch abortado ao gerar relatório: %s", exc)
        raise _downstream_http_error(exc) from exc
    return JSONResponse(summary)
