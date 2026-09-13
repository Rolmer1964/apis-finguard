"""Classificação de falhas de comunicação com o Amazon Bedrock.

Objetivo: transformar qualquer exceção do boto3/botocore num par
`(codigo, mensagem)` *específico e inequívoco*. Tanto o abort de startup
(`app.main`) quanto o HTTP 502 dos endpoints (`app.routers.risk`) usam isto
para dizer exatamente o que está errado — credencial ausente, SSO expirado,
sem permissão IAM, modelo inexistente, sem rede, throttling — em vez de um
genérico "Bedrock indisponível".

Cópia da versão genérica do `fin_triage`: o parâmetro `resource` é o recurso
Bedrock em jogo (aqui, o model id de risco) e as mensagens falam em
`bedrock:InvokeModel`.

Todo `codigo` retornado começa com o prefixo ``BEDROCK_``.
"""

from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

try:  # nomes que variam entre versões do botocore
    from botocore.exceptions import ConnectionError as _BotoConnectionError
except Exception:  # pragma: no cover - fallback defensivo
    _BotoConnectionError = ()

try:
    from botocore.exceptions import NoCredentialsError as _NoCredentialsError
except Exception:  # pragma: no cover
    _NoCredentialsError = ()

try:  # erro base do SDK da Anthropic (usado quando ANTHROPIC_API_KEY está definida)
    from anthropic import APIError as _AnthropicAPIError
except Exception:  # pragma: no cover - fallback defensivo
    _AnthropicAPIError = ()

# Exceções boto3/Anthropic que este módulo sabe classificar. Reexportado para
# os blocos `except` dos routers e do probe de startup.
BEDROCK_ERRORS = (BotoCoreError, ClientError) + (
    (_AnthropicAPIError,) if _AnthropicAPIError else ()
)

_INVALID_CRED_CODES = {
    "UnrecognizedClientException",
    "InvalidSignatureException",
    "InvalidClientTokenId",
    "InvalidAccessKeyId",
    "AuthFailure",
    "SignatureDoesNotMatch",
}
_EXPIRED_CODES = {"ExpiredTokenException", "ExpiredToken", "RequestExpired"}
_THROTTLE_CODES = {
    "ThrottlingException",
    "ThrottledException",
    "TooManyRequestsException",
    "Throttling",
    "RequestLimitExceeded",
}
_NOT_FOUND_CODES = {"ResourceNotFoundException"}


def aws_error_text(exc: BaseException) -> str:
    """Texto cru do erro AWS (código + mensagem), para o campo ``erro_aws``."""
    if isinstance(exc, ClientError) and getattr(exc, "response", None):
        err = exc.response.get("Error", {})
        code = err.get("Code") or "ClientError"
        msg = err.get("Message") or str(exc)
        return f"{code}: {msg}"
    return f"{type(exc).__name__}: {exc}"


def classify_bedrock_error(
    exc: BaseException,
    *,
    resource: str,
    region: str,
    profile: str | None = None,
) -> tuple[str, str]:
    """Mapeia ``exc`` para ``(codigo, mensagem)``.

    Nunca levanta: qualquer coisa que não seja reconhecida cai em
    ``BEDROCK_ERRO_DESCONHECIDO`` com o erro AWS anexado.
    """
    ctx = f"recurso='{resource}', regiao='{region}'"
    if profile:
        ctx += f", profile='{profile}'"

    name = type(exc).__name__
    aws_code = ""
    if isinstance(exc, ClientError) and getattr(exc, "response", None):
        aws_code = exc.response.get("Error", {}).get("Code", "") or ""

    # --- chamada direta à Anthropic API (ANTHROPIC_API_KEY definida) -------
    if _AnthropicAPIError and isinstance(exc, _AnthropicAPIError):
        return "ANTHROPIC_ERRO", (
            f"A chamada direta à Anthropic API falhou ({ctx}). "
            f"Erro: {name}: {exc}"
        )

    # --- credenciais -------------------------------------------------------
    if (_NoCredentialsError and isinstance(exc, _NoCredentialsError)) or name in (
        "NoCredentialsError",
        "PartialCredentialsError",
        "CredentialRetrievalError",
    ):
        return "BEDROCK_SEM_CREDENCIAIS", (
            f"Nenhuma credencial AWS foi encontrada para chamar o Bedrock ({ctx}). "
            "Defina AWS_PROFILE no .env e rode `aws sso login`, ou informe chaves "
            "estáticas (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY)."
        )

    if name == "ProfileNotFound":
        return "BEDROCK_PROFILE_INEXISTENTE", (
            f"O AWS_PROFILE '{profile}' não existe em ~/.aws/config ({ctx}). "
            "Corrija o nome no .env ou configure o profile (`aws configure sso`)."
        )

    if name == "NoRegionError":
        return "BEDROCK_REGIAO_AUSENTE", (
            "Nenhuma região AWS configurada para o Bedrock. Defina AWS_REGION no .env."
        )

    if name in (
        "SSOTokenLoadError",
        "UnauthorizedSSOTokenError",
        "TokenRetrievalError",
    ) or aws_code in _EXPIRED_CODES:
        alvo = profile or "<seu-profile>"
        return "BEDROCK_SSO_EXPIRADO", (
            f"A sessão AWS/SSO expirou ao chamar o Bedrock ({ctx}). "
            f"Rode `aws sso login --profile {alvo}` e suba a API novamente."
        )

    if aws_code in _INVALID_CRED_CODES:
        return "BEDROCK_CREDENCIAL_INVALIDA", (
            f"O Bedrock rejeitou as credenciais AWS ({ctx}). "
            "Confira AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN "
            "ou o profile usado."
        )

    if aws_code == "AccessDeniedException":
        return "BEDROCK_SEM_PERMISSAO", (
            f"Credencial AWS válida, mas o Bedrock negou a chamada: falta a permissão "
            f"IAM `bedrock:InvokeModel` para o {ctx}. Ajuste a policy da role/usuário."
        )

    # --- recurso / parâmetros ----------------------------------------------
    if aws_code in _NOT_FOUND_CODES or (
        aws_code == "ValidationException" and "model" in str(exc).lower()
    ):
        return "BEDROCK_RECURSO_NAO_ENCONTRADO", (
            f"O Bedrock não encontrou o recurso '{resource}' na região '{region}'. "
            "Verifique BEDROCK_MODEL_RISK e AWS_REGION no .env, e se o modelo está "
            "habilitado na conta."
        )

    if aws_code == "ValidationException":
        return "BEDROCK_REQUISICAO_INVALIDA", (
            f"O Bedrock recusou a requisição como inválida ({ctx}). "
            f"Erro AWS: {aws_error_text(exc)}"
        )

    # --- throttling ------------------------------------------------------------
    if aws_code in _THROTTLE_CODES:
        return "BEDROCK_THROTTLING", (
            f"O Bedrock está limitando (throttling) as chamadas ao {ctx}. "
            "Repita em instantes."
        )

    # --- conectividade -------------------------------------------------------
    if (_BotoConnectionError and isinstance(exc, _BotoConnectionError)) or name in (
        "EndpointConnectionError",
        "EndpointResolutionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
        "ConnectionClosedError",
        "ConnectionError",
        "SSLError",
        "ProxyConnectionError",
    ):
        return "BEDROCK_SEM_CONECTIVIDADE", (
            f"Não foi possível alcançar o endpoint do Amazon Bedrock na região "
            f"'{region}' ({ctx}). Verifique conexão de rede, DNS, proxy ou o VPC "
            "endpoint do bedrock-runtime."
        )

    # --- fallback ------------------------------------------------------------
    return "BEDROCK_ERRO_DESCONHECIDO", (
        f"Falha inesperada ao comunicar com o Amazon Bedrock ({ctx}). "
        f"Erro AWS: {aws_error_text(exc)}"
    )
