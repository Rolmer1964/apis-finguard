"""Testes da API. Log em memória, limpo entre testes (ver conftest.py)."""

from fastapi.testclient import TestClient

from app import trace_store
from app.main import app

client = TestClient(app)


def _entry(**over):
    e = {
        "trace_id": "R001",
        "text_preview": "cobrança dupla no cartão",
        "blocked": False,
        "category": "Cobrança Indevida",
        "urgency": "Crítica",
        "risk_level": "Alto",
        "product": "Cartão de Crédito",
        "canal": "Banco Central",
        "prazo_resposta": "4 horas",
        "area_responsavel": "Ouvidoria",
        "timings_ms": {"guardrail_input": 10, "triage": 100, "risk": 200, "report": 5},
    }
    e.update(over)
    return e


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_post_trace_preenche_timestamp_e_total_ms():
    resp = client.post("/v1/traces", json=_entry())
    assert resp.status_code == 201
    assert resp.json() == {"status": "stored", "count": 1}

    t = trace_store.get_traces()[0]
    assert t["timestamp"]  # preenchido
    assert t["total_ms"] == 315  # 10 + 100 + 200 + 5


def test_post_trace_respeita_total_ms_informado():
    client.post("/v1/traces", json=_entry(total_ms=999))
    assert trace_store.get_traces()[0]["total_ms"] == 999


def test_get_traces_context():
    client.post("/v1/traces", json=_entry(trace_id="A"))
    client.post("/v1/traces", json=_entry(trace_id="B", blocked=True, urgency=None, risk_level=None))

    ctx = client.get("/v1/traces").json()
    assert ctx["count"] == 2
    assert ctx["has_data"] is True
    assert set(ctx["st"]) == {"total_ms", "triage", "risk", "report"}
    disp = ctx["traces"][0]
    assert "bar_triage" in disp and disp["bar_triage"].endswith("px")
    assert "<span" in disp["urgency_html"] or disp["urgency_html"] == "—"


def test_traces_stats_puro():
    client.post("/v1/traces", json=_entry())
    st = client.get("/v1/traces/stats").json()
    assert set(st) == {"total_ms", "triage", "risk", "report"}
    assert st["triage"]["mean"] == 100


def test_decisorio_stats():
    client.post("/v1/traces", json=_entry(trace_id="A"))  # Crítica / Alto / Banco Central
    client.post("/v1/traces", json=_entry(trace_id="B", blocked=True, canal="Web"))
    client.post("/v1/traces", json=_entry(
        trace_id="C", canal="Web", urgency="Baixa", risk_level="Baixo",
        area_responsavel="Suporte", prazo_resposta="5 dias úteis",
    ))

    d = client.get("/v1/decisorio/stats").json()
    assert d["total"] == 3
    assert d["bloqueados"] == 1
    assert d["processados"] == 2
    assert d["matrix"]["Crítica"]["Alto"] == 1
    assert d["matrix"]["Baixa"]["Baixo"] == 1
    assert d["canais"]["Web"]["total"] == 2
    assert d["canais"]["Banco Central"]["critica"] == 1
    assert d["urgency"] == {"Crítica": 1, "Baixa": 1}
    assert d["areas"] == {"Ouvidoria": 1, "Suporte": 1}


def test_recompose_from_results():
    results = [
        {"id": "X1", "texto_original": "a" * 90, "category": "Atendimento",
         "urgency": "Alta", "risk_level": "Médio", "canal": "Chat",
         "timings_ms": {"triage": 50, "risk": 60, "report": 2}},
        {"id": "X2", "texto_original": "curto", "blocked": True, "canal": "Web",
         "timings_ms": {}},
    ]
    resp = client.post("/v1/traces/recompose", json={"results": results})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "recomposed": 2}

    data = trace_store.get_traces()
    assert len(data) == 2
    # ordem: X1 injetado por último (reversed) → topo do deque
    assert data[0]["trace_id"] == "X1"
    assert data[0]["text_preview"].endswith("…") and len(data[0]["text_preview"]) == 71
    assert data[0]["total_ms"] == 112


def test_delete_traces():
    client.post("/v1/traces", json=_entry())
    client.post("/v1/traces", json=_entry(trace_id="R002"))
    resp = client.request("DELETE", "/v1/traces")
    assert resp.json() == {"status": "ok", "cleared": 2}
    assert client.get("/v1/traces").json()["count"] == 0


def test_post_trace_sem_trace_id_e_422():
    assert client.post("/v1/traces", json={"blocked": False}).status_code == 422


def test_persistencia_sobrevive_reload(tmp_path):
    path = tmp_path / "traces.json"
    trace_store.configure_persistence(str(path))
    trace_store.append_trace(_entry(trace_id="P1"))
    trace_store.append_trace(_entry(trace_id="P2"))
    assert path.exists()

    # simula restart: processo novo tem deque vazio; só depois liga a persistência
    trace_store.configure_persistence(None)   # desliga o dump
    trace_store._traces.clear()               # deque "novo", sem tocar o arquivo
    trace_store.configure_persistence(str(path))  # recarrega do disco

    assert [d["trace_id"] for d in trace_store.get_traces()] == ["P2", "P1"]
