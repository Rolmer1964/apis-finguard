"""Schemas Pydantic para request/response da API."""

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto da reclamação bancária a classificar.")
    product_hint: str | None = Field(
        None, description="Produto sugerido pelo canal de origem — apenas uma pista, não uma certeza."
    )


class TriageResponse(BaseModel):
    category: str = Field(..., description="Cobrança Indevida | Atendimento | Fraude/Segurança | Produto/Serviço | Cancelamento | Outros.")
    product: str = Field(..., description="Cartão de Crédito | Conta Corrente | Empréstimo | Investimentos | Seguros | Não Identificado.")
    sentiment: str = Field(..., description="Positivo | Neutro | Negativo | Crítico.")
    urgency: str = Field(..., description="Baixa | Média | Alta | Crítica.")
    summary: str = Field(..., description="Resumo neutro de 2-3 linhas, com palavrões mascarados.")


class HealthResponse(BaseModel):
    status: str = "ok"
