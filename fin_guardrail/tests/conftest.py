"""Fixtures compartilhadas dos testes.

A API chama o Amazon Bedrock de verdade em produção; nos testes o método
`GuardrailService._apply` é substituído por um stub, então nada de AWS é
necessário. Também garantimos um GUARDRAIL_ID qualquer para o boot passar.
"""

import os

os.environ.setdefault("GUARDRAIL_ID", "test-guardrail")
os.environ.setdefault("GUARDRAIL_VERSION", "DRAFT")
os.environ.setdefault("AWS_REGION", "us-east-1")

import pytest  # noqa: E402

from app.guardrail_service import GuardrailService  # noqa: E402


def _fake_apply(self, source: str, text: str) -> dict:
    """Stub de Bedrock apply_guardrail.

    - INPUT: bloqueia se o texto contém marcadores óbvios de prompt injection;
      caso contrário libera.
    - OUTPUT: devolve o texto como veio, sem intervenção (a segunda camada de
      regex do serviço é quem faz o scrub de PII nos testes).
    """
    lowered = text.lower()
    if source == "INPUT":
        if "ignore" in lowered or "system prompt" in lowered:
            return {
                "action": "GUARDRAIL_INTERVENED",
                # Simula a "Messaging for blocked prompts" configurada no guardrail.
                "outputs": [{"text": "Não posso ajudar com isso. Envie uma reclamação bancária válida."}],
                "assessments": [
                    {"topicPolicy": {"topics": [{"name": "prompt-injection", "action": "BLOCKED"}]}}
                ],
            }
        return {"action": "NONE", "outputs": [], "assessments": []}
    return {"action": "NONE", "outputs": [{"text": text}], "assessments": []}


@pytest.fixture(autouse=True)
def stub_bedrock(monkeypatch):
    """Substitui a chamada real ao Bedrock em todos os testes."""
    monkeypatch.setattr(GuardrailService, "_apply", _fake_apply)
