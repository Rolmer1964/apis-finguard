"""Configurações do orquestrador: endereços das folhas + parâmetros de batch.

Não usa AWS. As credenciais ficam nas folhas de Bedrock (triage/rag/risk/
guardrail); aqui só circula a `API_KEY` compartilhada, repassada a cada folha
no header `X-API-Key`.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Endereços das folhas (em compose: http://<serviço>:<porta>) ---
    GUARDRAIL_URL: str = "http://localhost:8001"
    TRIAGE_URL: str = "http://localhost:8002"
    RAG_URL: str = "http://localhost:8003"
    RISK_URL: str = "http://localhost:8004"
    CONSOLIDATE_URL: str = "http://localhost:8005"
    REPORT_WRITER_URL: str = "http://localhost:8006"
    TRACES_URL: str = "http://localhost:8007"

    # Timeout (s) de cada chamada HTTP a uma folha.
    HTTP_TIMEOUT: float = 30.0

    # Repassada às folhas via X-API-Key. Se as folhas exigirem chave, use a mesma.
    API_KEY: Optional[str] = None

    # --- Batch / AIMD (portado da finguard8) ---
    BATCH_MAX_WORKERS: int = 5
    BATCH_RATE_LIMIT_DELAY: float = 0.0
    BATCH_MAX_RETRIES: int = 2
    BATCH_MAX_PASSES: int = 3
    BATCH_RETRY_DELAY: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def url_for(self, key: str) -> str:
        return getattr(self, key).rstrip("/")


@lru_cache
def get_settings() -> "Settings":
    return Settings()
