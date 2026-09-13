"""Testes dos proxies de leitura — respx intercepta o httpx do orquestrador."""

import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@respx.mock
def test_proxy_reports_repassa_json():
    route = respx.get("http://report-writer.test/v1/reports").mock(
        return_value=httpx.Response(200, json={"reports": [], "total": 0})
    )
    r = client.get("/reports")
    assert r.status_code == 200
    assert r.json() == {"reports": [], "total": 0}
    assert route.called


@respx.mock
def test_proxy_output_preserva_content_type():
    respx.get("http://report-writer.test/output/report_x.csv").mock(
        return_value=httpx.Response(200, text="id,canal\nR1,Web\n",
                                    headers={"content-type": "text/csv; charset=utf-8"})
    )
    r = client.get("/output/report_x.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert r.text.startswith("id,canal")


@respx.mock
def test_proxy_report_html():
    respx.get("http://report-writer.test/v1/reports/report_x/html").mock(
        return_value=httpx.Response(200, text="<html>ok</html>", headers={"content-type": "text/html"})
    )
    r = client.get("/reports/report_x/html")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "<html>" in r.text


@respx.mock
def test_proxy_recompose_encaminha_corpo():
    captured = {}

    def _resp(request):
        captured["body"] = request.content
        return httpx.Response(200, json={"status": "ok", "recomposed": 1})

    respx.post("http://traces.test/v1/traces/recompose").mock(side_effect=_resp)
    r = client.post("/traces/recompose", json={"results": [{"id": "X"}]})
    assert r.status_code == 200 and r.json()["recomposed"] == 1
    assert b'"results"' in captured["body"]


@respx.mock
def test_proxy_status_downstream_e_repassado():
    respx.get("http://report-writer.test/v1/reports/nope").mock(
        return_value=httpx.Response(404, json={"detail": "Relatório não encontrado"})
    )
    r = client.get("/reports/nope")
    assert r.status_code == 404
    assert r.json()["detail"] == "Relatório não encontrado"


@respx.mock
def test_proxy_rag_ingest():
    respx.post("http://rag.test/v1/rag/ingest").mock(
        return_value=httpx.Response(202, json={"status": "started"})
    )
    r = client.post("/rag/ingest")
    assert r.status_code == 202 and r.json()["status"] == "started"


@respx.mock
def test_proxy_folha_indisponivel_vira_503():
    respx.get("http://traces.test/v1/traces").mock(side_effect=httpx.ConnectError("recusou"))
    r = client.get("/traces")
    assert r.status_code == 503


def test_health_local():
    assert client.get("/health").json() == {"status": "ok"}


@respx.mock
def test_health_downstream_agrega():
    for host in ("guardrail", "triage", "rag", "risk", "consolidate", "report-writer", "traces"):
        respx.get(f"http://{host}.test/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    r = client.get("/health/downstream")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["services"]) == {
        "fin_guardrail", "fin_triage", "fin_rag", "fin_risk",
        "fin_consolidate", "fin_report_writer", "fin_traces",
    }
    assert all(v["ok"] for v in body["services"].values())


@respx.mock
def test_health_downstream_degradado_quando_folha_cai():
    for host in ("guardrail", "triage", "rag", "risk", "consolidate", "report-writer"):
        respx.get(f"http://{host}.test/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    respx.get("http://traces.test/health").mock(side_effect=httpx.ConnectError("down"))
    r = client.get("/health/downstream")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    assert r.json()["services"]["fin_traces"]["ok"] is False
