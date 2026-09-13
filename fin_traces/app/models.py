"""Schemas Pydantic para request/response da API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceEntry(BaseModel):
    """Uma entrada do log de execução (montada pelo `fin_orchestrator`)."""

    trace_id: str = Field(..., description="Id do registro / execução.")
    timestamp: str | None = Field(None, description="HH:MM:SS (BRT). Preenchido se ausente.")
    text_preview: str | None = Field("", description="Prévia do texto (até ~70 chars).")
    blocked: bool = Field(False, description="A execução foi barrada pelo guardrail de entrada.")
    category: str | None = None
    urgency: str | None = None
    risk_level: str | None = None
    product: str | None = None
    canal: str | None = None
    prazo_resposta: str | None = None
    area_responsavel: str | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict, description="Latência por etapa.")
    total_ms: int | None = Field(None, description="Total e2e. Somado de timings_ms se ausente.")

    # Tolera campos extras que o orquestrador queira anexar ao log.
    model_config = ConfigDict(extra="allow")


class RecomposeRequest(BaseModel):
    results: list[dict[str, Any]] = Field(
        ..., description="Lista `results` de um relatório batch (payload do fin_report_writer)."
    )


class StoreResponse(BaseModel):
    status: str = "stored"
    count: int = Field(..., description="Total de entradas no log após a inserção.")


class RecomposeResponse(BaseModel):
    status: str = "ok"
    recomposed: int


class ClearResponse(BaseModel):
    status: str = "ok"
    cleared: int


class HealthResponse(BaseModel):
    status: str = "ok"
