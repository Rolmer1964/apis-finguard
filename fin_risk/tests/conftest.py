"""Fixtures compartilhadas dos testes.

A API chama o Amazon Bedrock de verdade em produção; nos testes o método
`RiskService._call_llm` (a única chamada que toca a AWS) é substituído por
um stub. O probe de startup também fica desligado por padrão.
"""

import os

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("PROBE_ON_STARTUP", "false")

import pytest  # noqa: E402

from app.risk_service import RiskService  # noqa: E402


def _fake_call_llm(self, system, user, *, max_tokens=800, temperature=0.2):
    """Stub determinístico do Claude Sonnet.

    Devolve um JSON de risco plausível derivado de palavras-chave do texto.
    """
    low = user.lower()
    if "fraude" in low or "não reconheço" in low or "nao reconheco" in low:
        risco = "Crítico"
    elif "banco central" in low or "procon" in low or "processo judicial" in low:
        risco = "Alto"
    else:
        risco = "Médio"
    return (
        '{"risco": "%s", '
        '"justificativa": "Ha indicios que exigem atencao conforme §2.3 da POL-SAC-001.", '
        '"acoes_recomendadas": ["Abrir chamado prioritario", "Notificar a area responsavel"]}'
        % risco
    )


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    """Substitui a chamada real ao Bedrock em todos os testes."""
    monkeypatch.setattr(RiskService, "_call_llm", _fake_call_llm)
