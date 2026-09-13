"""Ações e proxies: envios redirecionam; proxies repassam; snake é local."""

import httpx
import respx

from .conftest import ORCH


@respx.mock
def test_analyze_form_redireciona_para_relatorio(client):
    stem = "report_2026-09-10-12-00-00"
    respx.post(f"{ORCH}/analyze-form").mock(return_value=httpx.Response(200, json={
        "stem": stem, "paths": {}, "result": {"trace_id": "t1"}}))
    r = client.post("/analyze-form", data={"text": "reclamação", "canal": "Web"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/report/{stem}"


@respx.mock
def test_analyze_form_propaga_502(client):
    respx.post(f"{ORCH}/analyze-form").mock(return_value=httpx.Response(
        502, json={"detail": {"service": "fin_triage", "downstream_status": 502}}))
    r = client.post("/analyze-form", data={"text": "x"}, follow_redirects=False)
    assert r.status_code == 502


@respx.mock
def test_batch_redireciona(client):
    stem = "report_2026-09-10-13-00-00"
    respx.post(f"{ORCH}/batch").mock(return_value=httpx.Response(200, json={"stem": stem}))
    r = client.post("/batch", files={"file": ("x.csv", b"texto_reclamacao\noi", "text/csv")},
                    data={"label": "teste"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/report/{stem}"


def test_batch_rejeita_nao_csv(client):
    r = client.post("/batch", files={"file": ("x.txt", b"oi", "text/plain")})
    assert r.status_code == 400


@respx.mock
def test_delete_report_repassa(client):
    stem = "report_2026-09-10-12-00-00"
    route = respx.delete(f"{ORCH}/reports/{stem}").mock(
        return_value=httpx.Response(200, json={"stem": stem, "removed_files": 3}))
    r = client.request("DELETE", f"/report/{stem}")
    assert r.status_code == 200
    assert route.called
    assert r.json()["removed_files"] == 3


@respx.mock
def test_traces_recompose_busca_json_e_posta_results(client):
    stem = "report_2026-09-10-12-00-00"
    items = [{"id": "REC-1", "texto_original": "oi"}, {"id": "REC-2", "texto_original": "ola"}]
    respx.get(f"{ORCH}/output/{stem}.json").mock(return_value=httpx.Response(200, json=items))
    posted = respx.post(f"{ORCH}/traces/recompose").mock(
        return_value=httpx.Response(200, json={"recomposed": 2}))
    r = client.post(f"/traces/recompose?stem={stem}")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "recomposed": 2}
    assert posted.called
    sent = httpx.Request("POST", f"{ORCH}/traces/recompose")  # sanity: body shape
    import json as _j
    assert _j.loads(posted.calls.last.request.content) == {"results": items}


@respx.mock
def test_decisorio_stats_proxy(client):
    respx.get(f"{ORCH}/decisorio/stats").mock(return_value=httpx.Response(200, json={"total": 5}))
    r = client.get("/api/decisorio/stats")
    assert r.status_code == 200
    assert r.json()["total"] == 5


@respx.mock
def test_record_proxy(client):
    respx.get(f"{ORCH}/records/REC-1").mock(return_value=httpx.Response(200, json={"id": "REC-1"}))
    r = client.get("/records/REC-1")
    assert r.status_code == 200
    assert r.json()["id"] == "REC-1"


@respx.mock
def test_ingest_proxy(client):
    respx.post(f"{ORCH}/rag/ingest").mock(return_value=httpx.Response(202, json={"status": "started"}))
    respx.get(f"{ORCH}/rag/ingest/status").mock(return_value=httpx.Response(200, json={"status": "done"}))
    assert client.post("/ingest").status_code == 202
    assert client.get("/ingest/status").json()["status"] == "done"


def test_snake_record_roundtrip(client):
    assert client.get("/snake/record").json() == {"record": 0, "date": ""}
    up = client.post("/snake/record", json={"record": 12, "date": "10/09/2026"})
    assert up.json() == {"status": "updated", "record": 12}
    assert client.get("/snake/record").json()["record"] == 12
    # não regride
    again = client.post("/snake/record", json={"record": 5, "date": "x"})
    assert again.json() == {"status": "no_update", "record": 12}
