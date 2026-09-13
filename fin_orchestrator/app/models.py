"""Schemas Pydantic do orquestrador.

O `/analyze` devolve o payload no mesmo shape da finguard8 (dict livre —
`trace_id, blocked, triage, risk, ...consolidado, timings_ms`), por isso não há
um modelo de resposta rígido para ele.
"""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto da reclamação bancária.")
    product_hint: str | None = Field(None, description="Produto sugerido pelo canal de origem.")
    canal: str | None = Field(None, description="Canal de origem (dispara overrides regulatórios na consolidação).")


class HealthResponse(BaseModel):
    status: str = "ok"
