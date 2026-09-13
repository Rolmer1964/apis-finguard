"""Schemas Pydantic para request/response da API."""

from typing import Any

from pydantic import BaseModel, Field


class ReportMeta(BaseModel):
    """Metadados da execução em batch (todos opcionais)."""

    started_at: str | None = Field(None, description="Início da execução (string livre, ex.: ISO).")
    finished_at: str | None = Field(None, description="Fim da execução.")
    elapsed_s: float | None = Field(None, description="Duração total em segundos.")
    pass_stats: list[dict[str, Any]] | None = Field(
        None, description="Estatísticas por passe do controle adaptativo (AIMD)."
    )
    label: str | None = Field(None, description="Identificação livre do relatório.")
    filename: str | None = Field(None, description="Nome do CSV de origem, se houver.")


class CreateReportRequest(BaseModel):
    results: list[dict[str, Any]] = Field(
        ..., min_length=1,
        description="Registros consolidados (com id, canal, texto_original, timings_ms, etc.).",
    )
    meta: ReportMeta = Field(default_factory=ReportMeta, description="Metadados da execução.")


class CreateReportResponse(BaseModel):
    stem: str = Field(..., description="Identificador do relatório: report_YYYY-MM-DD-HH-MM-SS.")
    paths: dict[str, str] = Field(
        ..., description="Caminhos absolutos dos artefatos gravados, com chaves json/csv/md."
    )


class DeleteReportResponse(BaseModel):
    status: str = "ok"
    stem: str
    removed_files: int


class HealthResponse(BaseModel):
    status: str = "ok"
