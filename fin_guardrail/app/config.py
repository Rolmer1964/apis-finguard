"""Configurações da aplicação, carregadas de variáveis de ambiente / .env."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- AWS / Bedrock ---
    # Região do Bedrock. As credenciais são resolvidas pela cadeia padrão do
    # boto3: variáveis de ambiente -> ~/.aws/credentials -> ~/.aws/config
    # (profile [default] ou AWS_PROFILE) -> IAM role da instância EC2 (IMDS).
    # Não é preciso preencher chave/segredo aqui a menos que você queira
    # forçar credenciais estáticas (dev).
    AWS_REGION: str = "us-east-1"
    # Nome do profile em ~/.aws/config a usar (ex.: um profile SSO ou de
    # assume-role). Se vazio, usa a cadeia padrão do boto3 (inclui a IAM role
    # da EC2). Tem precedência sobre as chaves estáticas abaixo.
    AWS_PROFILE: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # Guardrail de entrada (INPUT). OBRIGATÓRIO — a API chama o Amazon Bedrock
    # de verdade; se a chamada falhar, o endpoint retorna HTTP 502 (sem
    # fallback local).
    GUARDRAIL_ID: str = Field(min_length=1)
    GUARDRAIL_VERSION: str = "DRAFT"

    # Guardrail de saída (OUTPUT). Se vazio, usa GUARDRAIL_ID como fallback.
    GUARDRAIL_ID_OUTPUT: Optional[str] = None
    GUARDRAIL_VERSION_OUTPUT: str = "DRAFT"

    # --- API ---
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
