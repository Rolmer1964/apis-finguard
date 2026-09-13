"""Configurações da aplicação, carregadas de variáveis de ambiente / .env.

Este serviço é determinístico e NÃO usa AWS.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Se definido, o deque de traces é despejado neste arquivo (JSON) a cada
    # escrita e recarregado no startup — sobrevive a restart do processo.
    # Vazio (default) → log só em memória.
    TRACES_PERSIST_PATH: Optional[str] = None

    # Se definido, os endpoints de escrita exigem o header X-API-Key com esse valor.
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
