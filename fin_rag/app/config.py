"""Configurações da aplicação, carregadas de variáveis de ambiente / .env."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Embeddings ---
    # Modelo local (sentence-transformers) — roda dentro do próprio container,
    # sem chamada externa, sem credencial. Multilíngue (bom em português).
    EMBED_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBED_DIM: int = 384

    # --- RAG ---
    # Pasta com os documentos de política (PDF/MD/TXT). Relativo ao CWD em dev;
    # no Docker aponte para /app/assets/docs via env.
    RAG_DOCS_DIR: str = "assets/docs"
    # Pasta onde o índice FAISS + manifest são persistidos.
    RAG_INDEX_DIR: str = "assets/index"
    RAG_TOP_K: int = 4
    RAG_CHUNK_CHARS: int = 1000
    RAG_CHUNK_OVERLAP: int = 200

    # No startup: 1 embedding local para garantir que o modelo carregou
    # corretamente e abortar cedo se algo estiver errado.
    PROBE_ON_STARTUP: bool = True
    # No startup: dispara a ingestão incremental em background (só re-embeda
    # arquivos novos/alterados; se nada mudou, apenas carrega o índice).
    INGEST_ON_STARTUP: bool = True

    # --- API ---
    API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> "Settings":
    """Settings é cacheada (singleton) durante o ciclo de vida do processo."""
    return Settings()
