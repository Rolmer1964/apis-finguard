"""Testes da API. Gravam em disco num OUTPUT_DIR temporário (ver conftest.py)."""

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REC_CRIT = {
    "id": "R001",
    "canal": "Banco Central",
    "texto_original": "Fui cobrado em duplicidade e ninguém resolve.",
    "category": "Cobrança Indevida",
    "product": "Cartão de Crédito",
    "sentiment": "Crítico",
    "urgency": "Crítica",
    "summary": "Cliente relata cobrança dupla no cartão e ameaça acionar o Banco Central.",
    "prazo_resposta": "1 dia útil",
    "area_responsavel": "Ouvidoria",
    "risk_level": "Alto",
    "risk_justification": "Risco reputacional conforme §3.1 da POL-SAC-001.",
    "acoes_recomendadas": ["Abrir chamado prioritário", "Notificar a Ouvidoria"],
    "timings_ms": {"triage": 120, "risk": 300, "report": 4},
}
REC_OK = {
    "id": "R002",
    "canal": "Web",
    "texto_original": "App fora do ar ontem à noite.",
    "category": "Produto/Serviço",
    "product": "Conta Corrente",
    "sentiment": "Neutro",
    "urgency": "Baixa",
    "summary": "Instabilidade no app relatada pelo cliente.",
    "prazo_resposta": "5 dias úteis",
    "area_responsavel": "Suporte Técnico",
    "risk_level": "Baixo",
    "risk_justification": "Sem indício de fraude.",
    "acoes_recomendadas": [],
    "timings_ms": {"triage": 90, "risk": 150, "report": 3},
}


def _create(results=None, meta=None):
    body = {"results": results or [REC_CRIT, REC_OK]}
    if meta is not None:
        body["meta"] = meta
    return client.post("/v1/reports", json=body)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_grava_artefatos_e_retorna_stem(output_dir):
    resp = _create(meta={"label": "lote de teste", "filename": "reclamacoes.csv", "elapsed_s": 12.5})
    assert resp.status_code == 200
    body = resp.json()
    stem = body["stem"]
    assert re.fullmatch(r"report_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}", stem)
    assert set(body["paths"]) == {"json", "csv", "md"}
    for ext in (".json", ".csv", ".md", ".meta.json"):
        assert (output_dir / f"{stem}{ext}").exists()


def test_create_sem_meta_nao_gera_meta_json(output_dir):
    stem = _create().json()["stem"]
    assert (output_dir / f"{stem}.json").exists()
    assert not (output_dir / f"{stem}.meta.json").exists()


def test_create_results_vazio_e_422():
    assert client.post("/v1/reports", json={"results": []}).status_code == 422


def test_list_reports():
    stem = _create().json()["stem"]
    body = client.get("/v1/reports").json()
    assert body["total"] == 1
    entry = body["reports"][0]
    assert entry["stem"] == stem
    assert entry["has_csv"] and entry["has_md"] and entry["has_json"]


def test_get_report_context():
    stem = _create().json()["stem"]
    ctx = client.get(f"/v1/reports/{stem}").json()
    assert ctx["total"] == 2
    assert ctx["by_category"]["Cobrança Indevida"] == 1
    assert len(ctx["critical"]) == 1 and ctx["critical"][0]["id"] == "R001"
    assert ctx["by_canal"]["Banco Central"] == 1


def test_get_report_html():
    stem = _create().json()["stem"]
    resp = client.get(f"/v1/reports/{stem}/html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "FinGuard" in resp.text
    assert "R001" in resp.text
    assert f"/v1/reports/{stem}/record/" in resp.text  # RECORD_ENDPOINT injetado


def test_get_report_inexistente_404():
    assert client.get("/v1/reports/report_2020-01-01-00-00-00").status_code == 404


def test_get_record_por_id():
    stem = _create().json()["stem"]
    rec = client.get(f"/v1/reports/{stem}/record/R002").json()
    assert rec["id"] == "R002"
    assert rec["area_responsavel"] == "Suporte Técnico"


def test_get_record_id_inexistente_404():
    stem = _create().json()["stem"]
    assert client.get(f"/v1/reports/{stem}/record/NAO_EXISTE").status_code == 404


def test_get_record_stem_inexistente_404():
    assert client.get("/v1/reports/report_2020-01-01-00-00-00/record/R001").status_code == 404


def test_get_record_global_varre_todos_os_relatorios():
    stem = _create().json()["stem"]
    rec = client.get("/v1/records/R001").json()
    assert rec["id"] == "R001" and rec["canal"] == "Banco Central"
    assert stem  # só para deixar claro que o registro veio de um relatório salvo


def test_get_record_global_inexistente_404():
    _create()
    assert client.get("/v1/records/NAO_EXISTE").status_code == 404


def test_serve_output_raw():
    stem = _create().json()["stem"]
    resp = client.get(f"/output/{stem}.json")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "R001"


def test_serve_output_rejeita_traversal():
    assert client.get("/output/..%2F..%2Fetc%2Fpasswd").status_code in (400, 404)
    assert client.get("/output/nao_existe.json").status_code == 404


def test_delete_report():
    stem = _create(meta={"label": "x"}).json()["stem"]
    resp = client.request("DELETE", f"/v1/reports/{stem}")
    assert resp.status_code == 200
    assert resp.json()["removed_files"] == 4
    assert client.get(f"/v1/reports/{stem}").status_code == 404


def test_delete_report_stem_invalido_400():
    assert client.request("DELETE", "/v1/reports/xpto").status_code == 400


def test_delete_report_inexistente_404():
    assert client.request("DELETE", "/v1/reports/report_2020-01-01-00-00-00").status_code == 404
