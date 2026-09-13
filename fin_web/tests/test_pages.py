"""Telas SSR: cada rota busca dados no orquestrador (mockado) e renderiza."""

import httpx
import respx

from .conftest import ORCH


def _report_ctx(results):
    return {
        "results": results,
        "total": len(results),
        "critical": [r for r in results if (r.get("urgency") or "").startswith("Crít")],
        "by_category": {"Fraude": 1},
        "by_product": {"Cartão": 1},
        "by_urgency": {"Crítica": 1},
        "by_risk": {"Alto": 1},
        "by_sentiment": {"Negativo": 1},
        "by_canal": {"Web": 1},
        "recommendations": ["Rever POL-SAC-001 §4.3"],
        "generated_at": "2026-09-10T12:00:00-03:00",
        "started_at": "2026-09-10 11:59:00 (UTC-3)",
        "finished_at": "2026-09-10 12:00:00 (UTC-3)",
        "elapsed_s": 60.0,
        "elapsed_fmt": "1min 00s",
        "pass_stats": [],
    }


def test_index_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Reclamação individual" in r.text
    assert 'action="/analyze-form"' in r.text


def test_health_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


@respx.mock
def test_reports_page_lists(client):
    respx.get(f"{ORCH}/reports").mock(return_value=httpx.Response(200, json={
        "reports": [{"stem": "report_2026-09-10-12-00-00", "ts_display": "report_2026-09-10-12-00-00",
                     "size_kb": 1.2, "has_json": True, "has_csv": True, "has_md": True,
                     "label": "Consulta unitária", "filename": ""}],
        "total": 1,
    }))
    r = client.get("/reports")
    assert r.status_code == 200
    assert "report_2026-09-10-12-00-00" in r.text
    assert "/report/report_2026-09-10-12-00-00" in r.text


@respx.mock
def test_report_detail_renders(client):
    stem = "report_2026-09-10-12-00-00"
    results = [{"id": "REC-1", "canal": "Web", "category": "Fraude", "product": "Cartão",
                "sentiment": "Negativo", "urgency": "Crítica", "risk_level": "Alto",
                "summary": "resumo", "risk_justification": "just", "acoes_recomendadas": []}]
    respx.get(f"{ORCH}/reports/{stem}").mock(return_value=httpx.Response(200, json=_report_ctx(results)))
    r = client.get(f"/report/{stem}")
    assert r.status_code == 200
    assert "Relatório Gerencial" in r.text
    assert "REC-1" in r.text
    # modal aponta para o proxy do fin_web, não para o fin_report_writer
    assert "'/records/' + encodeURIComponent(id)" in r.text
    assert f"/output/{stem}.json" in r.text


@respx.mock
def test_report_detail_404_propaga(client):
    stem = "report_inexistente"
    respx.get(f"{ORCH}/reports/{stem}").mock(return_value=httpx.Response(404, json={"detail": "Relatório não encontrado"}))
    r = client.get(f"/report/{stem}")
    assert r.status_code == 404


@respx.mock
def test_traces_page_renders(client):
    respx.get(f"{ORCH}/traces").mock(return_value=httpx.Response(200, json={
        "count": 1, "has_data": True,
        "st": {"total_ms": {"mean": 10, "stdev": 1, "cv": 10.0, "median": 10, "p95": 12, "p99": 13},
               "triage": {"mean": 3, "stdev": 0, "cv": 0.0, "median": 3, "p95": 3, "p99": 3},
               "risk": {"mean": 4, "stdev": 0, "cv": 0.0, "median": 4, "p95": 4, "p99": 4},
               "report": {"mean": 1, "stdev": 0, "cv": 0.0, "median": 1, "p95": 1, "p99": 1}},
        "traces": [{"trace_id": "abc123", "text_preview": "reclamação", "blocked": False,
                    "category": "Fraude", "urgency_html": "<span>Crítica</span>",
                    "risk_level_html": "<span>Alto</span>", "t_ms": 3, "r_ms": 4, "rp_ms": 1,
                    "gi_ms": 2, "total_display": 10, "bar_triage": "24px", "bar_risk": "32px",
                    "bar_report": "8px"}],
    }))
    r = client.get("/traces")
    assert r.status_code == 200
    assert "abc123" in r.text
    assert "Log de Execuções — 1 registro(s)" in r.text


@respx.mock
def test_admin_page_aggregates(client):
    respx.get(f"{ORCH}/reports").mock(return_value=httpx.Response(200, json={"reports": [], "total": 3}))
    respx.get(f"{ORCH}/rag/stats").mock(return_value=httpx.Response(200, json={
        "total_vectors": 42, "files": [{"path": "KS_POLITICA_INTERNA.pdf", "chunks": 9, "hash": "x"}]}))
    respx.get(f"{ORCH}/traces").mock(return_value=httpx.Response(200, json={"count": 7}))
    r = client.get("/admin")
    assert r.status_code == 200
    assert ">3<" in r.text
    assert ">42<" in r.text
    assert ">7<" in r.text
    assert "KS_POLITICA_INTERNA.pdf" in r.text


@respx.mock
def test_admin_degrada_sem_orquestrador(client):
    respx.get(f"{ORCH}/reports").mock(side_effect=httpx.ConnectError("boom"))
    respx.get(f"{ORCH}/rag/stats").mock(side_effect=httpx.ConnectError("boom"))
    respx.get(f"{ORCH}/traces").mock(side_effect=httpx.ConnectError("boom"))
    r = client.get("/admin")
    assert r.status_code == 200  # página ainda abre, só com zeros/erro


def test_politica_decisoria_renders(client):
    r = client.get("/politica-decisoria")
    assert r.status_code == 200
    assert "/api/decisorio/stats" in r.text


def test_adr_and_relatorio_tecnico(client):
    assert client.get("/adr").status_code == 200
    assert client.get("/relatorio-tecnico").status_code == 200
