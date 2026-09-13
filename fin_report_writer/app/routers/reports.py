"""Endpoints de relatórios: geração, listagem, detalhe, HTML, registro e remoção.

Portado das rotas de relatório de `finguard8/app/src/main.py`
(`_build_reports_context`, `_load_report_context`, `/report/{stem}`,
`/report/{stem}` DELETE, `/api/record/{id}`, mount `/output`). Aqui tudo fica
sob `/v1/reports/...`, exceto `/output/{filename}` que serve o artefato bruto.
"""

import json as _json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..config import Settings, get_settings
from ..dependencies import verify_api_key
from ..models import CreateReportRequest, CreateReportResponse, DeleteReportResponse
from ..report_writer import build_report_context, render_report_html, write_outputs
from ..timeutil import now_brt

logger = logging.getLogger("fin_report_writer.api")

router = APIRouter(tags=["reports"])

# Formato do stem gerado por este serviço (compatível com o glob e o
# regex de exclusão herdados do monólito).
_STEM_RE = re.compile(r"report_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}")
_FILENAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def _out_dir(settings: Settings) -> Path:
    return Path(settings.OUTPUT_DIR)


def _build_reports_context(out_dir: Path) -> dict:
    json_files = sorted(
        [f for f in out_dir.glob("report_*.json") if not f.name.endswith(".meta.json")],
        reverse=True,
    )

    def _read_meta(stem: str) -> dict:
        meta = out_dir / f"{stem}.meta.json"
        if meta.exists():
            try:
                return _json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _report_entry(f: Path) -> dict:
        meta = _read_meta(f.stem)
        return {
            "stem": f.stem,
            "ts_display": f.stem,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "has_json": True,
            "has_csv": (out_dir / f"{f.stem}.csv").exists(),
            "has_md": (out_dir / f"{f.stem}.md").exists(),
            "label": meta.get("label", ""),
            "filename": meta.get("filename", ""),
        }

    reports = [_report_entry(f) for f in json_files]
    return {"reports": reports, "total": len(json_files)}


def _load_report_context(out_dir: Path, stem: str) -> dict:
    json_path = out_dir / f"{stem}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    results = _json.loads(json_path.read_text(encoding="utf-8"))
    meta_path = out_dir / f"{stem}.meta.json"
    meta = _json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return build_report_context(results, meta)


@router.post(
    "/v1/reports",
    response_model=CreateReportResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Gera os artefatos (JSON/CSV/MD) de uma execução em batch",
)
def create_report(
    payload: CreateReportRequest,
    settings: Settings = Depends(get_settings),
) -> CreateReportResponse:
    stem = now_brt().strftime("report_%Y-%m-%d-%H-%M-%S")
    m = payload.meta
    paths = write_outputs(
        payload.results,
        settings.OUTPUT_DIR,
        stem=stem,
        started_at=m.started_at,
        finished_at=m.finished_at,
        elapsed_s=m.elapsed_s,
        pass_stats=m.pass_stats,
        label=m.label,
        filename=m.filename,
    )
    logger.info("relatório gerado: %s (%d registro(s))", stem, len(payload.results))
    return CreateReportResponse(stem=stem, paths=paths)


@router.get("/v1/reports", summary="Lista os relatórios gerados (mais recentes primeiro)")
def list_reports(settings: Settings = Depends(get_settings)) -> dict:
    return _build_reports_context(_out_dir(settings))


@router.get("/v1/reports/{stem}", summary="Contexto agregado de um relatório (JSON)")
def get_report(stem: str, settings: Settings = Depends(get_settings)) -> dict:
    return _load_report_context(_out_dir(settings), stem)


@router.get(
    "/v1/reports/{stem}/html",
    response_class=HTMLResponse,
    summary="Relatório gerencial renderizado (report.html.j2)",
)
def get_report_html(stem: str, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    ctx = _load_report_context(_out_dir(settings), stem)
    return HTMLResponse(render_report_html(stem, ctx))


@router.get(
    "/v1/reports/{stem}/record/{record_id}",
    summary="Registro completo por id dentro de um relatório",
)
def get_record(stem: str, record_id: str, settings: Settings = Depends(get_settings)) -> JSONResponse:
    json_path = _out_dir(settings) / f"{stem}.json"
    if not json_path.exists():
        raise HTTPException(404, f"Relatório '{stem}' não encontrado")
    try:
        items = _json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - arquivo corrompido
        raise HTTPException(500, f"Relatório '{stem}' ilegível: {exc}") from exc
    if isinstance(items, list):
        for item in items:
            if item.get("id") == record_id:
                return JSONResponse(item)
    raise HTTPException(404, f"Registro '{record_id}' não encontrado em '{stem}'")


@router.get(
    "/v1/records/{record_id}",
    summary="Registro completo por id, varrendo todos os relatórios (mais recentes primeiro)",
)
def get_record_global(record_id: str, settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Equivalente ao `/api/record/{id}` do monólito. Usado pelo modal da tela
    de traces (onde não há um `stem` de contexto)."""
    out_dir = _out_dir(settings)
    for json_file in sorted(out_dir.glob("report_*.json"), reverse=True):
        if json_file.name.endswith(".meta.json"):
            continue
        try:
            items = _json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(items, list):
            for item in items:
                if item.get("id") == record_id:
                    return JSONResponse(item)
    raise HTTPException(404, f"Registro '{record_id}' não encontrado nos relatórios salvos")


@router.delete(
    "/v1/reports/{stem}",
    response_model=DeleteReportResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Remove os artefatos (.json/.meta.json/.csv/.md) de um relatório",
)
def delete_report(stem: str, settings: Settings = Depends(get_settings)) -> DeleteReportResponse:
    if not _STEM_RE.fullmatch(stem):
        raise HTTPException(status_code=400, detail="stem inválido")
    out_dir = _out_dir(settings)
    removed = 0
    for ext in (".json", ".meta.json", ".csv", ".md"):
        f = out_dir / f"{stem}{ext}"
        if f.exists():
            f.unlink()
            removed += 1
    if removed == 0:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    logger.info("report deletado: %s (%d arquivo(s))", stem, removed)
    return DeleteReportResponse(stem=stem, removed_files=removed)


@router.get("/output/{filename}", summary="Serve o artefato bruto (json/csv/md/meta)")
def serve_output(filename: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    if not _FILENAME_RE.fullmatch(filename):
        raise HTTPException(status_code=400, detail="nome de arquivo inválido")
    out_dir = _out_dir(settings).resolve()
    target = (out_dir / filename).resolve()
    if out_dir not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="arquivo não encontrado")
    return FileResponse(target)
