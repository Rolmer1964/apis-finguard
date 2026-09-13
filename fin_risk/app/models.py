"""Schemas Pydantic para request/response da API."""

from pydantic import BaseModel, Field


class TriageInput(BaseModel):
    """Resultado da triagem prévia (saída do `fin_triage`)."""

    category: str = Field(..., description="Categoria da reclamação.")
    product: str = Field(..., description="Produto financeiro envolvido.")
    sentiment: str = Field(..., description="Sentimento do cliente.")
    urgency: str = Field(..., description="Urgência: Baixa | Média | Alta | Crítica.")
    summary: str = Field(..., description="Resumo neutro da reclamação.")


class RiskRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto original da reclamação bancária.")
    triage: TriageInput = Field(..., description="Resultado da triagem prévia.")
    policy_context: str | None = Field(
        None,
        description=(
            "Trechos relevantes da Política Interna, já formatados pelo `fin_rag` "
            "(`policy_context`). Ausente → o serviço usa um aviso de índice vazio."
        ),
    )
    rag_chunks_count: int | None = Field(
        None,
        ge=0,
        description=(
            "Quantidade de trechos que compõem o `policy_context`. Repassado como "
            "`rag_chunks_used` na resposta (0 quando ausente)."
        ),
    )


class RiskResponse(BaseModel):
    risk_level: str = Field(..., description="Baixo | Médio | Alto | Crítico.")
    risk_justification: str = Field(..., description="2-3 frases citando a seção da POL-SAC-001.")
    acoes_recomendadas: list[str] = Field(
        default_factory=list, description="Ações imediatas obrigatórias (§2/§3 da POL-SAC-001), no máx. 5."
    )
    rag_chunks_used: int = Field(..., ge=0, description="Nº de trechos da política usados no prompt.")


class HealthResponse(BaseModel):
    status: str = "ok"
