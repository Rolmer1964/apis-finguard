"""Testes da API. Não tocam a AWS: o Bedrock é stubado em conftest.py
(fixture autouse `stub_llm`)."""

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.risk_service import EMPTY_POLICY_CONTEXT, RiskService

client = TestClient(app)

TRIAGE = {
    "category": "Fraude/Segurança",
    "product": "Cartão de Crédito",
    "sentiment": "Crítico",
    "urgency": "Crítica",
    "summary": "Cliente relata transação não reconhecida no cartão.",
}


def _body(**over):
    b = {"text": "Tem uma compra que eu não reconheço, é fraude.", "triage": TRIAGE}
    b.update(over)
    return b


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_risk_retorna_os_quatro_campos():
    resp = client.post("/v1/risk", json=_body())
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"risk_level", "risk_justification", "acoes_recomendadas", "rag_chunks_used"}
    assert body["risk_level"] == "Crítico"
    assert "POL-SAC-001" in body["risk_justification"]
    assert isinstance(body["acoes_recomendadas"], list) and body["acoes_recomendadas"]


def test_policy_context_e_count_sao_repassados(monkeypatch):
    capturado = {}

    def spy(self, system, user, *, max_tokens=800, temperature=0.2):
        capturado["user"] = user
        return '{"risco": "Alto", "justificativa": "x §1 da POL-SAC-001", "acoes_recomendadas": []}'

    monkeypatch.setattr(RiskService, "_call_llm", spy)
    resp = client.post(
        "/v1/risk",
        json=_body(policy_context="Trechos relevantes da Política Interna:\n\n[1] Fonte: KS", rag_chunks_count=3),
    )
    assert resp.status_code == 200
    assert resp.json()["rag_chunks_used"] == 3
    assert "Trechos relevantes da Política Interna" in capturado["user"]


def test_sem_policy_context_usa_aviso_e_zero_chunks(monkeypatch):
    capturado = {}

    def spy(self, system, user, *, max_tokens=800, temperature=0.2):
        capturado["user"] = user
        return '{"risco": "Médio", "justificativa": "y §2 da POL-SAC-001", "acoes_recomendadas": []}'

    monkeypatch.setattr(RiskService, "_call_llm", spy)
    resp = client.post("/v1/risk", json=_body())
    assert resp.status_code == 200
    assert resp.json()["rag_chunks_used"] == 0
    assert EMPTY_POLICY_CONTEXT in capturado["user"]


def test_json_invalido_do_modelo_cai_em_defaults(monkeypatch):
    monkeypatch.setattr(RiskService, "_call_llm", lambda self, s, u, **k: "desculpe, não consegui")
    resp = client.post("/v1/risk", json=_body(rag_chunks_count=2))
    assert resp.status_code == 200
    assert resp.json() == {
        "risk_level": "Baixo",
        "risk_justification": "",
        "acoes_recomendadas": [],
        "rag_chunks_used": 2,
    }


def test_bedrock_error_returns_502_com_codigo_especifico(monkeypatch):
    def boom(self, s, u, **k):
        raise ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "no perms"}},
            "InvokeModel",
        )

    monkeypatch.setattr(RiskService, "_call_llm", boom)
    resp = client.post("/v1/risk", json=_body())
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["codigo"] == "BEDROCK_SEM_PERMISSAO"
    assert "AccessDeniedException" in detail["erro_aws"]


def test_text_vazio_e_422():
    assert client.post("/v1/risk", json=_body(text="")).status_code == 422


def test_triage_ausente_e_422():
    assert client.post("/v1/risk", json={"text": "algo"}).status_code == 422


def test_rag_chunks_count_negativo_e_422():
    assert client.post("/v1/risk", json=_body(rag_chunks_count=-1)).status_code == 422


def test_startup_probe_ok_com_stub(monkeypatch):
    # stub_llm (autouse) faz o ping do startup passar sem tocar a AWS.
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(PROBE_ON_STARTUP=True, AWS_REGION="us-east-1"))
    with TestClient(app):
        pass


def test_startup_probe_aborta_sem_bedrock(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(PROBE_ON_STARTUP=True, AWS_REGION="us-east-1"))

    def boom(self):
        raise EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com/")

    monkeypatch.setattr(RiskService, "ping", boom)
    with pytest.raises(RuntimeError, match="BEDROCK_SEM_CONECTIVIDADE"):
        with TestClient(app):
            pass
