"""Rotas GET que renderizam as telas (SSR).

Cada tela busca os dados no `fin_orchestrator` (proxies de leitura) e passa o
contexto para o template. Os templates de relatório (`report.html.j2`,
`reports.html.j2`, `_modal.html.j2`, `_style`, `_header`) foram copiados do
`fin_report_writer`; os demais, do monólito. As URLs de nav/asset/modal
resolvem no próprio `fin_web`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..orchestrator import OrchestratorError, get_json
from ..templating import templates

logger = logging.getLogger("fin_web.pages")
router = APIRouter(tags=["pages"])

_ASSETS = Path(__file__).parent.parent / "assets"


def _orch_or_503(exc: OrchestratorError):
    """404 do orquestrador vira 404; qualquer outra falha vira 502."""
    status = exc.status_code if exc.status_code == 404 else 502
    raise HTTPException(status_code=status, detail=exc.detail)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html.j2")


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    try:
        ctx = get_json("/reports")
    except OrchestratorError as exc:
        _orch_or_503(exc)
    return templates.TemplateResponse(request, "reports.html.j2", ctx)


@router.get("/report/{stem}", response_class=HTMLResponse)
def report_detail(request: Request, stem: str):
    try:
        ctx = get_json(f"/reports/{stem}")
    except OrchestratorError as exc:
        _orch_or_503(exc)
    return templates.TemplateResponse(request, "report.html.j2", {"stem": stem, **ctx})


@router.get("/traces", response_class=HTMLResponse)
def traces_page(request: Request):
    try:
        ctx = get_json("/traces")
    except OrchestratorError as exc:
        _orch_or_503(exc)
    return templates.TemplateResponse(request, "traces.html.j2", ctx)


@router.get("/politica-decisoria", response_class=HTMLResponse)
def politica_decisoria_page(request: Request):
    # Os números vêm client-side de GET /api/decisorio/stats (ver actions.py).
    return templates.TemplateResponse(request, "politica_decisoria.html.j2")


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """Estado agregado (read-only) + ação de re-ingestão do RAG.

    Sem os botões de "zerar": o orquestrador não expõe proxy para `rag/reset`,
    `DELETE /traces` nem remoção em massa de relatórios.
    """
    ctx = {"n_out": 0, "n_vec": -1, "n_traces": 0, "docs": [],
           "guardrail_id": None, "guardrail_ver": "—"}
    try:
        ctx["n_out"] = get_json("/reports").get("total", 0)
    except OrchestratorError as exc:
        logger.warning("admin: /reports indisponível: %s", exc)
    try:
        rag = get_json("/rag/stats")
        ctx["n_vec"] = rag.get("total_vectors", -1)
        ctx["docs"] = [f.get("path", f) if isinstance(f, dict) else f
                       for f in rag.get("files", [])]
    except OrchestratorError as exc:
        logger.warning("admin: /rag/stats indisponível: %s", exc)
    try:
        ctx["n_traces"] = get_json("/traces").get("count", 0)
    except OrchestratorError as exc:
        logger.warning("admin: /traces indisponível: %s", exc)
    return templates.TemplateResponse(request, "admin.html.j2", ctx)


@router.get("/adr", response_class=HTMLResponse)
def adr_page():
    f = _ASSETS / "adr.html"
    if f.exists():
        return HTMLResponse(f.read_text(encoding="utf-8"))
    return HTMLResponse("<p>ADR não encontrado.</p>", status_code=404)


@router.get("/relatorio-tecnico", response_class=HTMLResponse)
def relatorio_tecnico_page():
    f = _ASSETS / "relatorio-tecnico.html"
    if f.exists():
        return HTMLResponse(f.read_text(encoding="utf-8"))
    return HTMLResponse("<p>Relatório Técnico de Entrega não encontrado.</p>", status_code=404)
