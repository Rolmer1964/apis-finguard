"""Proxies finos de leitura para o `fin_web`.

Repasse 1:1 (status, corpo, content-type) para o serviço dono. Sem lógica.
O orquestrador é o único que conhece o endereço de cada folha, então o
`fin_web` fala só com ele.
"""

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..config import get_settings

logger = logging.getLogger("fin_orchestrator.proxy")

router = APIRouter(tags=["proxy"])


async def _forward(url_key: str, path: str, request: Request) -> Response:
    s = get_settings()
    target = s.url_for(url_key) + path
    body = await request.body()

    headers = {}
    if s.API_KEY:
        headers["X-API-Key"] = s.API_KEY
    if request.headers.get("content-type"):
        headers["content-type"] = request.headers["content-type"]

    try:
        async with httpx.AsyncClient(timeout=s.HTTP_TIMEOUT) as c:
            r = await c.request(
                request.method, target,
                params=request.query_params, content=body or None, headers=headers,
            )
    except httpx.RequestError as exc:
        logger.warning("proxy %s %s -> sem resposta: %s", request.method, target, exc)
        return Response(
            content=f'{{"detail":"folha indisponível ({url_key}): {exc}"}}',
            status_code=503, media_type="application/json",
        )

    passthru = {}
    if r.headers.get("content-disposition"):
        passthru["content-disposition"] = r.headers["content-disposition"]
    return Response(
        content=r.content, status_code=r.status_code,
        media_type=r.headers.get("content-type"), headers=passthru,
    )


# ── fin_report_writer ────────────────────────────────────────────────────────

@router.get("/reports")
async def reports(request: Request):
    return await _forward("REPORT_WRITER_URL", "/v1/reports", request)


@router.get("/reports/{stem}/html")
async def report_html(stem: str, request: Request):
    return await _forward("REPORT_WRITER_URL", f"/v1/reports/{stem}/html", request)


@router.get("/reports/{stem}")
async def report_detail(stem: str, request: Request):
    return await _forward("REPORT_WRITER_URL", f"/v1/reports/{stem}", request)


@router.delete("/reports/{stem}")
async def report_delete(stem: str, request: Request):
    return await _forward("REPORT_WRITER_URL", f"/v1/reports/{stem}", request)


@router.get("/records/{record_id}")
async def record(record_id: str, request: Request):
    return await _forward("REPORT_WRITER_URL", f"/v1/records/{record_id}", request)


@router.get("/output/{filename}")
async def output(filename: str, request: Request):
    return await _forward("REPORT_WRITER_URL", f"/output/{filename}", request)


# ── fin_traces ───────────────────────────────────────────────────────────────

@router.get("/traces")
async def traces(request: Request):
    return await _forward("TRACES_URL", "/v1/traces", request)


@router.get("/decisorio/stats")
async def decisorio_stats(request: Request):
    return await _forward("TRACES_URL", "/v1/decisorio/stats", request)


@router.post("/traces/recompose")
async def traces_recompose(request: Request):
    return await _forward("TRACES_URL", "/v1/traces/recompose", request)


# ── fin_rag ──────────────────────────────────────────────────────────────────

@router.get("/rag/stats")
async def rag_stats(request: Request):
    return await _forward("RAG_URL", "/v1/rag/stats", request)


@router.post("/rag/ingest")
async def rag_ingest(request: Request):
    return await _forward("RAG_URL", "/v1/rag/ingest", request)


@router.get("/rag/ingest/status")
async def rag_ingest_status(request: Request):
    return await _forward("RAG_URL", "/v1/rag/ingest/status", request)
