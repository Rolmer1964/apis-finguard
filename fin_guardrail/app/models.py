"""Schemas Pydantic para request/response da API."""

from typing import Optional

from pydantic import BaseModel, Field


class GuardrailInputRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto de entrada a ser validado (ex.: reclamação bruta do cliente).")


class GuardrailInputResponse(BaseModel):
    blocked: bool = Field(..., description="True se a entrada foi bloqueada pelo guardrail.")
    reason: Optional[str] = Field(None, description="Motivo técnico/interno do bloqueio (para logs).")
    block_reason: Optional[str] = Field(None, description="Detalhe do(s) tópico(s)/filtro(s) do Bedrock que acionaram o bloqueio.")
    message: Optional[str] = Field(
        None,
        description=(
            "Mensagem para exibir ao cliente quando blocked=True. Vem da resposta de "
            "bloqueio configurada no guardrail do Bedrock (outputs[].text); se o Bedrock "
            "não devolver texto, cai no BLOCKED_INPUT_MESSAGE local. Null quando não há bloqueio."
        ),
    )
    sanitized_text: str = Field(..., description="Texto de entrada (não sanitizado no input; devolvido para conveniência do chamador).")


class GuardrailOutputRequest(BaseModel):
    text: str = Field(..., description="Texto de saída (ex.: resposta de um agente) a ser sanitizado.")
    field: str = Field("", description="Nome do campo/etapa de origem, usado apenas para logging.")


class GuardrailOutputResponse(BaseModel):
    sanitized_text: str = Field(..., description="Texto sanitizado, com PII e violações tratadas/removidas.")
    meta: dict = Field(default_factory=dict, description="Detalhes do que foi encontrado/alterado (PII, intervenção do Bedrock, etc.).")


class HealthResponse(BaseModel):
    status: str = "ok"
