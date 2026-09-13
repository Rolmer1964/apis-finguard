"""Rotas de ação e proxies finos para o browser.

Envios (`/analyze-form`, `/batch`) repassam o form ao orquestrador e devolvem
um **303** para `/report/{stem}` (igual ao monólito). Os demais são repasse
1:1 para um proxy do orquestrador, exceto:
- `POST /traces/recompose?stem=` — o monólito lia o `OUTPUT_DIR`; aqui o
  fin_web busca o JSON do relatório e manda `{results}` ao `fin_traces`;
- `GET|POST /snake/record` — estado local (JSON no disco do fin_web).
"""

from __future__ import annotations

import json as _json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import get_settings
from ..orchestrator import OrchestratorError, forward, get_json, post_json

logger = logging.getLogger("fin_web.actions")
router = APIRouter(tags=["actions"])


def _auth_headers() -> dict:
    key = get_settings().API_KEY
    return {"X-API-Key": key} if key else {}


# ── Envios: repassa o form e redireciona para o relatório ────────────────────

@router.post("/analyze-form")
def analyze_form(
    text: str = Form(...),
    product_hint: str = Form(""),
    canal: str = Form("Web"),
) -> RedirectResponse:
    s = get_settings()
    try:
        with httpx.Client(base_url=s.orch, timeout=s.HTTP_TIMEOUT) as c:
            r = c.post(
                "/analyze-form", headers=_auth_headers(),
                data={"text": text, "product_hint": product_hint, "canal": canal},
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, f"orquestrador indisponível: {exc}") from exc
    if r.status_code // 100 != 2:
        _raise_from_response(r)
    stem = r.json().get("stem")
    return RedirectResponse(url=f"/report/{stem}", status_code=303)


@router.post("/batch")
async def batch(file: UploadFile = File(...), label: str = Form("")) -> RedirectResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Envie um arquivo .csv")
    raw = await file.read()
    s = get_settings()
    try:
        async with httpx.AsyncClient(base_url=s.orch, timeout=s.HTTP_TIMEOUT) as c:
            r = await c.post(
                "/batch", headers=_auth_headers(),
                data={"label": label},
                files={"file": (file.filename, raw, "text/csv")},
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, f"orquestrador indisponível: {exc}") from exc
    if r.status_code // 100 != 2:
        _raise_from_response(r)
    stem = r.json().get("stem")
    return RedirectResponse(url=f"/report/{stem}", status_code=303)


def _raise_from_response(r: httpx.Response) -> None:
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        detail = r.text
    raise HTTPException(r.status_code, detail)


# ── Relatórios: deletar + recompor log ──────────────────────────────────────

@router.delete("/report/{stem}")
async def delete_report(request: Request, stem: str):
    return await forward(request, f"/reports/{stem}")


@router.post("/traces/recompose")
def traces_recompose(stem: str) -> JSONResponse:
    """Reconstrói o log a partir do `results` de um relatório salvo.

    O `fin_traces` recebe `{results:[...]}` no corpo (não lê disco), então o
    fin_web busca o JSON bruto do relatório via `GET {ORCH}/output/{stem}.json`.
    """
    try:
        items = get_json(f"/output/{stem}.json")
    except OrchestratorError as exc:
        raise HTTPException(exc.status_code, exc.detail)
    if not isinstance(items, list):
        raise HTTPException(502, f"relatório '{stem}' com formato inesperado")
    try:
        out = post_json("/traces/recompose", json={"results": items})
    except OrchestratorError as exc:
        raise HTTPException(exc.status_code, exc.detail)
    return JSONResponse({"status": "ok", "recomposed": out.get("recomposed", len(items))})


# ── Proxies finos consumidos por JS das telas ───────────────────────────────

@router.get("/api/decisorio/stats")
async def decisorio_stats(request: Request):
    return await forward(request, "/decisorio/stats")


@router.get("/records/{record_id}")
async def record(request: Request, record_id: str):
    return await forward(request, f"/records/{record_id}")


@router.get("/output/{filename}")
async def output(request: Request, filename: str):
    return await forward(request, f"/output/{filename}")


@router.post("/ingest")
async def ingest(request: Request):
    return await forward(request, "/rag/ingest")


@router.get("/ingest/status")
async def ingest_status(request: Request):
    return await forward(request, "/rag/ingest/status")


# ── Snake: recorde local (tela de espera do batch) ──────────────────────────

def _snake_path() -> Path:
    return Path(get_settings().SNAKE_RECORD_PATH)


@router.get("/snake/record")
def snake_record_get() -> JSONResponse:
    p = _snake_path()
    if p.exists():
        return JSONResponse(_json.loads(p.read_text(encoding="utf-8")))
    return JSONResponse({"record": 0, "date": ""})


@router.post("/snake/record")
def snake_record_post(body: dict) -> JSONResponse:
    record = int(body.get("record", 0))
    date = str(body.get("date", ""))
    p = _snake_path()
    current = 0
    if p.exists():
        current = _json.loads(p.read_text(encoding="utf-8")).get("record", 0)
    if record <= current:
        return JSONResponse({"status": "no_update", "record": current})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_json.dumps({"record": record, "date": date}, ensure_ascii=False), encoding="utf-8")
    logger.info("snake record atualizado: %d (%s)", record, date)
    return JSONResponse({"status": "updated", "record": record})
