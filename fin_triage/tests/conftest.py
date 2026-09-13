"""Fixtures compartilhadas dos testes.

A API chama o Amazon Bedrock de verdade em produção; nos testes o método
`TriageService._call_llm` (a única chamada que toca a AWS) é substituído por
um stub. O probe de startup também fica desligado por padrão.
"""

import os

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("PROBE_ON_STARTUP", "false")

import pytest  # noqa: E402

from app.triage_service import TriageService  # noqa: E402


def _fake_call_llm(self, system, user, *, max_tokens=600, temperature=0.1):
    """Stub determinístico do Claude Haiku.

    Devolve um JSON de triagem plausível derivado de palavras-chave do texto.
    """
    low = user.lower()
    if "não reconheço" in low or "nao reconheco" in low or "fraude" in low:
        categoria, urgencia = "Fraude/Segurança", "Crítica"
    elif "banco central" in low or "procon" in low:
        categoria, urgencia = "Cobrança Indevida", "Crítica"
    else:
        categoria, urgencia = "Cobrança Indevida", "Alta"
    return (
        '{"categoria": "%s", "produto": "Cartão de Crédito", '
        '"sentimento": "Negativo", "urgencia": "%s", '
        '"resumo": "Cliente relata cobranca indevida na fatura do cartao."}'
        % (categoria, urgencia)
    )


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    """Substitui a chamada real ao Bedrock em todos os testes."""
    monkeypatch.setattr(TriageService, "_call_llm", _fake_call_llm)
