"""Testes da API. Não requerem AWS nem rede — a consolidação é determinística."""

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def _payload(**over):
    base = {
        "triage": {
            "category": "Cobrança Indevida",
            "product": "Cartão de Crédito",
            "sentiment": "Negativo",
            "urgency": "Baixa",
            "summary": "Cliente relata cobrança em duplicidade.",
        },
        "risk": {
            "risk_level": "Baixo",
            "risk_justification": "Sem indício de fraude.",
            "acoes_recomendadas": ["Abrir chamado", "Contatar o cliente"],
        },
        "canal": None,
    }
    base.update(over)
    return base


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_consolidacao_basica_deriva_sla_e_area():
    resp = client.post("/v1/consolidate", json=_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["urgency"] == "Baixa"
    assert body["prazo_resposta"] == "5 dias úteis"
    assert body["area_responsavel"] == "Gerência de Cartões"
    assert body["risk_level"] == "Baixo"
    assert body["risk_level_original"] is None
    assert body["acoes_recomendadas"] == ["Abrir chamado", "Contatar o cliente"]


def test_produto_desconhecido_cai_em_suporte_geral():
    resp = client.post("/v1/consolidate", json=_payload(triage={
        "category": "Outros", "product": "Consórcio", "sentiment": "Neutro",
        "urgency": "Média", "summary": "x",
    }))
    body = resp.json()
    assert body["area_responsavel"] == "Área de Suporte Geral"
    assert body["prazo_resposta"] == "3 dias úteis"


def test_risco_critico_eleva_urgencia_minima_para_alta():
    resp = client.post("/v1/consolidate", json=_payload(
        risk={"risk_level": "Crítico", "risk_justification": "Fraude confirmada.", "acoes_recomendadas": []},
    ))
    body = resp.json()
    assert body["urgency"] == "Alta"
    assert body["prazo_resposta"] == "24 horas"
    # Sem canal regulatório: risco não é alterado, só a urgência.
    assert body["risk_level"] == "Crítico"
    assert body["risk_level_original"] is None


def test_canal_regulatorio_forca_urgencia_critica_e_risco_minimo_alto():
    resp = client.post("/v1/consolidate", json=_payload(canal="Banco Central"))
    body = resp.json()
    assert body["urgency"] == "Crítica"
    assert body["prazo_resposta"] == "4 horas"
    assert body["risk_level"] == "Alto"
    assert body["risk_level_original"] == "Baixo"
    assert "POL-SAC-001 §4.3" in body["risk_justification"]


def test_canal_regulatorio_nao_rebaixa_risco_ja_maior():
    resp = client.post("/v1/consolidate", json=_payload(
        canal="Procon",
        risk={"risk_level": "Crítico", "risk_justification": "j", "acoes_recomendadas": []},
    ))
    body = resp.json()
    assert body["risk_level"] == "Crítico"
    assert body["risk_level_original"] is None


def test_api_key_exigida_quando_configurada():
    app.dependency_overrides[get_settings] = lambda: Settings(API_KEY="segredo")
    try:
        assert client.post("/v1/consolidate", json=_payload()).status_code == 401
        ok = client.post("/v1/consolidate", json=_payload(), headers={"X-API-Key": "segredo"})
        assert ok.status_code == 200
    finally:
        app.dependency_overrides.clear()
