"""Testes da API. Não tocam a AWS: o Bedrock é stubado em conftest.py
(fixture autouse `stub_llm`)."""

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.triage_service import TriageService

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_triage_retorna_os_cinco_campos():
    resp = client.post("/v1/triage", json={"text": "Fui cobrado duas vezes na fatura do meu cartão."})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"category", "product", "sentiment", "urgency", "summary"}
    assert body["category"] == "Cobrança Indevida"
    assert body["product"] == "Cartão de Crédito"
    assert body["urgency"] == "Alta"


def test_triage_fraude_vira_critica():
    resp = client.post("/v1/triage", json={"text": "Tem uma compra que eu não reconheço, é fraude."})
    assert resp.json()["urgency"] == "Crítica"
    assert resp.json()["category"] == "Fraude/Segurança"


def test_produto_invalido_do_modelo_cai_em_nao_identificado(monkeypatch):
    def weird_product(self, system, user, *, max_tokens=600, temperature=0.1):
        return '{"categoria": "Outros", "produto": "Consórcio", "sentimento": "Neutro", "urgencia": "Baixa", "resumo": "x"}'

    monkeypatch.setattr(TriageService, "_call_llm", weird_product)
    resp = client.post("/v1/triage", json={"text": "reclamação qualquer sobre consórcio"})
    assert resp.json()["product"] == "Não Identificado"


def test_product_hint_usado_quando_modelo_nao_devolve_produto(monkeypatch):
    def no_product(self, system, user, *, max_tokens=600, temperature=0.1):
        return '{"categoria": "Atendimento", "sentimento": "Neutro", "urgencia": "Baixa", "resumo": "x"}'

    monkeypatch.setattr(TriageService, "_call_llm", no_product)
    resp = client.post("/v1/triage", json={"text": "fila demorada na agência", "product_hint": "Conta Corrente"})
    assert resp.json()["product"] == "Conta Corrente"


def test_resumo_tem_palavrao_mascarado(monkeypatch):
    def rude(self, system, user, *, max_tokens=600, temperature=0.1):
        return '{"categoria": "Atendimento", "produto": "Conta Corrente", "sentimento": "Crítico", "urgencia": "Alta", "resumo": "O atendimento foi uma merda completa."}'

    monkeypatch.setattr(TriageService, "_call_llm", rude)
    resp = client.post("/v1/triage", json={"text": "atendimento pessimo"})
    assert "merda" not in resp.json()["summary"]
    assert "***" in resp.json()["summary"]


def test_json_invalido_do_modelo_cai_em_defaults(monkeypatch):
    monkeypatch.setattr(TriageService, "_call_llm", lambda self, s, u, **k: "desculpe, não consegui")
    resp = client.post("/v1/triage", json={"text": "algo"})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "category": "Outros", "product": "Não Identificado",
        "sentiment": "Neutro", "urgency": "Baixa", "summary": "",
    }


def test_bedrock_error_returns_502_com_codigo_especifico(monkeypatch):
    def boom(self, s, u, **k):
        raise ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "no perms"}},
            "InvokeModel",
        )

    monkeypatch.setattr(TriageService, "_call_llm", boom)
    resp = client.post("/v1/triage", json={"text": "uma reclamação qualquer aqui"})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["codigo"] == "BEDROCK_SEM_PERMISSAO"
    assert "AccessDeniedException" in detail["erro_aws"]


def test_text_vazio_e_422():
    assert client.post("/v1/triage", json={"text": ""}).status_code == 422


def test_startup_probe_ok_com_stub(monkeypatch):
    # stub_llm (autouse) faz o ping do startup passar sem tocar a AWS.
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(PROBE_ON_STARTUP=True, AWS_REGION="us-east-1"))
    with TestClient(app):
        pass


def test_startup_probe_aborta_sem_bedrock(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(PROBE_ON_STARTUP=True, AWS_REGION="us-east-1"))

    def boom(self):
        raise EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com/")

    monkeypatch.setattr(TriageService, "ping", boom)
    with pytest.raises(RuntimeError, match="BEDROCK_SEM_CONECTIVIDADE"):
        with TestClient(app):
            pass
