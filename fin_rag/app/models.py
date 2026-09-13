"""Schemas Pydantic para request/response da API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Consulta em texto livre (ex.: reclamação + dimensões da triagem).")
    k: Optional[int] = Field(None, ge=1, le=50, description="Quantos trechos retornar. Default: RAG_TOP_K.")


class ChunkOut(BaseModel):
    text: str
    source: str = Field(..., description="Arquivo de origem do trecho (caminho relativo em RAG_DOCS_DIR).")
    chunk_idx: int = Field(..., description="Índice do trecho dentro do arquivo.")
    score: float = Field(..., description="Similaridade (produto interno de vetores normalizados; ~1.0 = idêntico).")


class RetrieveResponse(BaseModel):
    chunks: List[ChunkOut]
    count: int
    policy_context: str = Field(
        ...,
        description=(
            "Trechos já formatados como bloco de contexto, prontos para injetar no "
            "prompt do fin_risk. Aviso fixo quando o índice está vazio."
        ),
    )


class IngestStartResponse(BaseModel):
    status: str = Field(..., description='"started" ou "already_running".')


class IngestStatusResponse(BaseModel):
    status: str = Field(..., description="idle | running | done | error.")
    stats: Optional[dict] = Field(None, description="Resumo da última ingestão concluída.")
    error: Optional[str] = Field(None, description="Mensagem de erro se status == error.")


class FileStat(BaseModel):
    path: str
    chunks: int
    hash: str


class StatsResponse(BaseModel):
    total_vectors: int
    files: List[FileStat]
    updated_at: Optional[str] = None


class ResetResponse(BaseModel):
    removed_index_files: int
    status: str


class HealthResponse(BaseModel):
    status: str = "ok"
