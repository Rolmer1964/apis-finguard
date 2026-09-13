"""Configurações da aplicação, carregadas de variáveis de ambiente / .env.

Este serviço é determinístico e NÃO usa AWS — a única configuração é a chave
opcional de API.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Se definido, os endpoints exigem o header X-API-Key com esse valor.
    # Deixe vazio em desenvolvimento local para não exigir autenticação.
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
