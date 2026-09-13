"""Testes do classificador de erros do Bedrock (`app/bedrock_errors.py`).

Não tocam a AWS: as exceções boto3 são instanciadas à mão.
"""

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)

from app.bedrock_errors import classify_bedrock_error

KW = dict(guardrail_id="gr-123", region="us-east-1", profile="finguard")


def _client_error(code: str, msg: str = "erro", op: str = "ApplyGuardrail") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": msg}}, op)


def test_sem_credenciais():
    codigo, msg = classify_bedrock_error(NoCredentialsError(), **KW)
    assert codigo == "BEDROCK_SEM_CREDENCIAIS"
    assert "credencial" in msg.lower()


def test_profile_inexistente():
    codigo, _ = classify_bedrock_error(ProfileNotFound(profile="finguard"), **KW)
    assert codigo == "BEDROCK_PROFILE_INEXISTENTE"


def test_sso_expirado():
    codigo, msg = classify_bedrock_error(_client_error("ExpiredTokenException"), **KW)
    assert codigo == "BEDROCK_SSO_EXPIRADO"
    assert "aws sso login" in msg


def test_credencial_invalida():
    codigo, _ = classify_bedrock_error(_client_error("UnrecognizedClientException"), **KW)
    assert codigo == "BEDROCK_CREDENCIAL_INVALIDA"


def test_sem_permissao():
    codigo, _ = classify_bedrock_error(_client_error("AccessDeniedException"), **KW)
    assert codigo == "BEDROCK_SEM_PERMISSAO"


def test_guardrail_nao_encontrado_resource_not_found():
    codigo, msg = classify_bedrock_error(_client_error("ResourceNotFoundException"), **KW)
    assert codigo == "BEDROCK_GUARDRAIL_NAO_ENCONTRADO"
    assert "gr-123" in msg


def test_guardrail_nao_encontrado_validation_com_texto():
    exc = _client_error("ValidationException", "guardrail identifier is invalid")
    codigo, _ = classify_bedrock_error(exc, **KW)
    assert codigo == "BEDROCK_GUARDRAIL_NAO_ENCONTRADO"


def test_throttling():
    codigo, _ = classify_bedrock_error(_client_error("ThrottlingException"), **KW)
    assert codigo == "BEDROCK_THROTTLING"


def test_sem_conectividade():
    exc = EndpointConnectionError(endpoint_url="https://x")
    codigo, msg = classify_bedrock_error(exc, **KW)
    assert codigo == "BEDROCK_SEM_CONECTIVIDADE"
    assert "us-east-1" in msg


def test_desconhecido_anexa_erro_aws():
    codigo, msg = classify_bedrock_error(_client_error("WeirdNewError", "algo"), **KW)
    assert codigo == "BEDROCK_ERRO_DESCONHECIDO"
    assert "WeirdNewError" in msg
