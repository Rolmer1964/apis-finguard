"""Criação do client `bedrock-runtime` com resolução de credenciais.

Extraído de `fin_guardrail/app/guardrail_service.py::_bedrock_runtime`. Ordem
de resolução:
1. AWS_PROFILE (profile de ~/.aws/config — SSO, assume-role, etc.);
2. chaves estáticas (AWS_ACCESS_KEY_ID/...) se definidas no .env;
3. cadeia padrão do boto3: ~/.aws/credentials, profile [default],
   IAM role da instância EC2 (IMDS).
"""

import boto3

from .config import Settings


def bedrock_runtime(settings: Settings):
    session_kwargs: dict = {}
    if settings.AWS_PROFILE:
        session_kwargs["profile_name"] = settings.AWS_PROFILE

    client_kwargs: dict = {"region_name": settings.AWS_REGION}
    if not settings.AWS_PROFILE and settings.AWS_ACCESS_KEY_ID:
        client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

    return boto3.Session(**session_kwargs).client("bedrock-runtime", **client_kwargs)
