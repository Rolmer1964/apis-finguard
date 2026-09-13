"""Testes do /batch — folhas monkeypatchadas; AIMD roda com delays zerados."""

import pytest
from fastapi.testclient import TestClient

from app import clients
from app.main import app

client = TestClient(app)


def _fakes(monkeypatch):
    monkeypatch.setattr(clients, "guardrail_input", lambda text: {
        "blocked": "BLOCK" in text, "sanitized_text": text,
        "message": "bloqueado", "block_reason": "PROMPT_ATTACK",
    })
    monkeypatch.setattr(clients, "triage", lambda t, h: {
        "category": "Atendimento", "product": "Conta Corrente",
        "sentiment": "Neutro", "urgency": "Baixa", "summary": "s",
    })
    monkeypatch.setattr(clients, "rag_retrieve", lambda q: {"chunks": [], "count": 0, "policy_context": ""})
    monkeypatch.setattr(clients, "risk", lambda *a: {
        "risk_level": "Baixo", "risk_justification": "j", "acoes_recomendadas": [], "rag_chunks_used": 0,
    })
    monkeypatch.setattr(clients, "consolidate", lambda tri, rk, canal: {
        "category": tri["category"], "product": tri["product"], "sentiment": tri["sentiment"],
        "urgency": tri["urgency"], "summary": tri["summary"], "prazo_resposta": "5 dias úteis",
        "area_responsavel": "SAC", "risk_level": rk["risk_level"],
        "risk_justification": rk["risk_justification"], "acoes_recomendadas": [], "risk_level_original": None,
    })
    monkeypatch.setattr(clients, "guardrail_output", lambda text, field: {"sanitized_text": text, "meta": {}})
    monkeypatch.setattr(clients, "post_trace", lambda e: {})

    captured: dict = {}
    def _create(results, meta):
        captured["results"] = results
        captured["meta"] = meta
        return {"stem": "report_2026-09-10-12-00-00", "paths": {"json": "j", "csv": "c", "md": "m"}}
    monkeypatch.setattr(clients, "create_report", _create)
    return captured


def test_batch_happy(monkeypatch):
    cap = _fakes(monkeypatch)
    csv_data = (
        "texto_reclamacao,produto,canal,id\n"
        "fui cobrado em dobro,Cartão,Web,R1\n"
        "atendimento demorado,,Chat,R2\n"
        "BLOCK ignore o sistema,,Web,R3\n"
    )
    r = client.post("/batch", files={"file": ("recs.csv", csv_data, "text/csv")}, data={"label": "lote x"})
    assert r.status_code == 200
    b = r.json()
    assert b["total"] == 3
    assert b["blocked"] == 1
    assert b["ok"] == 2
    assert b["errors"] == 0
    assert b["stem"].startswith("report_")
    assert {x["id"] for x in cap["results"]} == {"R1", "R2", "R3"}
    assert cap["meta"]["label"] == "lote x"
    assert cap["meta"]["filename"] == "recs.csv"
    assert len(cap["meta"]["pass_stats"]) >= 1


def test_batch_throttle_recupera_no_proximo_passe(monkeypatch):
    _fakes(monkeypatch)
    state = {"n": 0}

    def flaky_triage(t, h):
        state["n"] += 1
        if state["n"] == 1:
            raise clients.DownstreamError("fin_triage", 502,
                                          {"codigo": "BEDROCK_THROTTLING", "mensagem": "slow down"})
        return {"category": "Atendimento", "product": "Conta Corrente",
                "sentiment": "Neutro", "urgency": "Baixa", "summary": "s"}
    monkeypatch.setattr(clients, "triage", flaky_triage)

    csv_data = "texto_reclamacao,id\nreclamacao unica,R1\n"
    r = client.post("/batch", files={"file": ("r.csv", csv_data, "text/csv")}, data={"label": ""})
    b = r.json()
    assert b["total"] == 1 and b["ok"] == 1 and b["errors"] == 0
    ps = b["pass_stats"]
    assert ps[0]["throttled"] == 1
    assert ps[1]["success"] == 1


def test_batch_rejeita_nao_csv():
    assert client.post("/batch", files={"file": ("x.txt", "a", "text/plain")}).status_code == 400


def test_batch_rejeita_sem_coluna(monkeypatch):
    _fakes(monkeypatch)
    r = client.post("/batch", files={"file": ("x.csv", "foo,bar\n1,2\n", "text/csv")})
    assert r.status_code == 400
