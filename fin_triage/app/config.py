"""Configurações da aplicação, carregadas de variáveis de ambiente / .env."""

from functools import lru_cache
from typing import Optional

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- AWS / Bedrock ---
    # Região do Bedrock. As credenciais são resolvidas pela cadeia padrão do
    # boto3: AWS_PROFILE -> chaves estáticas -> ~/.aws/* -> IAM role da EC2 (IMDS).
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # Modelo de triagem. Haiku: barato, classificação simples.
    BEDROCK_MODEL_TRIAGE: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    # Se definida, ignora o Bedrock e chama a Anthropic API diretamente com
    # esta chave (usa o mesmo BEDROCK_MODEL_TRIAGE, convertido para o id
    # nativo da Anthropic). Contorna o gate de acesso a modelos Claude no
    # Bedrock enquanto a conta não tem aprovação da AWS.
    ANTHROPIC_API_KEY: Optional[str] = None

    # Nome do parâmetro no SSM Parameter Store (SecureString) de onde buscar
    # ANTHROPIC_API_KEY quando ela não vier definida acima. Busca é feita uma
    # única vez, no startup (get_settings() é cacheada pro processo todo) —
    # nunca por requisição. Deixe vazio para não tocar no SSM (ex.: testes).
    ANTHROPIC_API_KEY_SSM_PARAM: Optional[str] = None

    # No startup, faz uma chamada real de 1 token ao Bedrock para verificar
    # conectividade e abortar cedo se algo estiver errado (credencial, permissão,
    # rede). Custa ~1 token de saída. Deixe "false" para pular (ex.: CI/testes).
    PROBE_ON_STARTUP: bool = True

    # --- API ---
    # Se definido, os endpoints exigem o header X-API-Key com esse valor.
    API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if self.ANTHROPIC_API_KEY or not self.ANTHROPIC_API_KEY_SSM_PARAM:
            return
        session_kwargs: dict = {}
        if self.AWS_PROFILE:
            session_kwargs["profile_name"] = self.AWS_PROFILE
        client_kwargs: dict = {"region_name": self.AWS_REGION}
        if not self.AWS_PROFILE and self.AWS_ACCESS_KEY_ID:
            client_kwargs["aws_access_key_id"] = self.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = self.AWS_SECRET_ACCESS_KEY
            if self.AWS_SESSION_TOKEN:
                client_kwargs["aws_session_token"] = self.AWS_SESSION_TOKEN
        ssm = boto3.Session(**session_kwargs).client("ssm", **client_kwargs)
        try:
            resp = ssm.get_parameter(Name=self.ANTHROPIC_API_KEY_SSM_PARAM, WithDecryption=True)
        except Exception as exc:
            raise RuntimeError(
                f"[SSM_ERRO] Falha ao buscar '{self.ANTHROPIC_API_KEY_SSM_PARAM}' "
                f"do Parameter Store: {exc}"
            ) from exc
        self.ANTHROPIC_API_KEY = resp["Parameter"]["Value"]


@lru_cache
def get_settings() -> "Settings":
    """Settings é cacheada (singleton) durante o ciclo de vida do processo."""
    return Settings()
