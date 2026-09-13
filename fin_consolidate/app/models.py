"""Schemas Pydantic para request/response da API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TriageInput(BaseModel):
    """Resultado da triagem (saída do fin_triage)."""

    category: Optional[str] = Field(None, description="Categoria da reclamação.")
    product: Optional[str] = Field(None, description="Produto identificado.")
    sentiment: Optional[str] = Field(None, description="Sentimento do cliente.")
    urgency: Optional[str] = Field(None, description="Urgência: Baixa | Média | Alta | Crítica.")
    summary: Optional[str] = Field(None, description="Resumo neutro da reclamação.")


class RiskInput(BaseModel):
    """Resultado da análise de risco (saída do fin_risk)."""

    risk_level: Optional[str] = Field(None, description="Nível de risco: Baixo | Médio | Alto | Crítico.")
    risk_justification: Optional[str] = Field("", description="Justificativa do nível de risco.")
    acoes_recomendadas: List[str] = Field(default_factory=list, description="Ações imediatas recomendadas.")


class ConsolidateRequest(BaseModel):
    triage: TriageInput
    risk: RiskInput
    canal: Optional[str] = Field(
        None,
        description=(
            "Canal de origem da reclamação. 'Banco Central', 'Procon' e 'Justiça' "
            "disparam os overrides regulatórios da POL-SAC-001 §4.3."
        ),
    )


class ConsolidateResponse(BaseModel):
    category: Optional[str] = None
    product: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = Field(None, description="Urgência após os overrides POL-SAC-001.")
    summary: Optional[str] = None
    prazo_resposta: Optional[str] = Field(None, description="SLA derivado da urgência final.")
    area_responsavel: Optional[str] = Field(None, description="Área responsável derivada do produto.")
    risk_level: Optional[str] = Field(None, description="Nível de risco após os overrides POL-SAC-001.")
    risk_justification: Optional[str] = Field(None, description="Justificativa, com a nota do override anexada quando aplicável.")
    acoes_recomendadas: List[str] = Field(default_factory=list)
    risk_level_original: Optional[str] = Field(
        None,
        description="Nível de risco antes do override de canal regulatório. Ausente quando não houve override.",
    )


class HealthResponse(BaseModel):
    status: str = "ok"
