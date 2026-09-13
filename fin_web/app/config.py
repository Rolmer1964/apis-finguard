"""Configurações do fin_web: endereço do orquestrador + auth.

O `fin_web` NÃO usa AWS e NÃO conhece o endereço de nenhuma folha — fala
**só** com o `fin_orchestrator`, que é o ponto único de entrada.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE = Path(__file__).parent


class Settings(BaseSettings):
    # Endereço do orquestrador (em compose: http://fin_orchestrator:8000).
    ORCHESTRATOR_URL: str = "http://localhost:8000"

    # Timeout (s) de cada chamada ao orquestrador. O /batch pode ser longo.
    HTTP_TIMEOUT: float = 120.0

    # Repassada ao orquestrador via X-API-Key (que a repassa às folhas).
    API_KEY: Optional[str] = None

    # Recorde do jogo da cobrinha da tela de espera do batch (JSON local).
    SNAKE_RECORD_PATH: str = str(_BASE / "assets" / "snake_record.json")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def orch(self) -> str:
        return self.ORCHESTRATOR_URL.rstrip("/")


@lru_cache
def get_settings() -> "Settings":
    return Settings()
