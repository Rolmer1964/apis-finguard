"""Endpoints de guardrail: validação de entrada e sanitização de saída."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..bedrock_errors import BEDROCK_ERRORS, aws_error_text, classify_bedrock_error
from ..config import Settings, get_settings
from ..dependencies import get_guardrail_service, verify_api_key
from ..guardrail_service import BLOCKED_INPUT_MESSAGE, GuardrailService
from ..models import (
    GuardrailInputRequest,
    GuardrailInputResponse,
    GuardrailOutputRequest,
    GuardrailOutputResponse,
)

logger = logging.getLogger("fin_guardrail.api")

router = APIRouter(prefix="/v1/guardrail", tags=["guardrail"])


def _bedrock_unavailable(exc: Exception, settings: Settings) -> HTTPException:
    """Converte um erro boto3 num HTTP 502 com causa específica e inequívoca.

    `detail` é um objeto `{codigo, mensagem, erro_aws}` — o `codigo`
    (ex.: BEDROCK_SEM_PERMISSAO, BEDROCK_SSO_EXPIRADO,
    BEDROCK_GUARDRAIL_NAO_ENCONTRADO, BEDROCK_SEM_CONECTIVIDADE) permite ao
    chamador reagir sem parsear texto livre.
    """
    codigo, mensagem = classify_bedrock_error(
        exc,
        guardrail_id=settings.GUARDRAIL_ID,
        region=settings.AWS_REGION,
        profile=settings.AWS_PROFILE,
    )
    logger.exception("Bedrock indisponível [%s]: %s", codigo, mensagem)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"codigo": codigo, "mensagem": mensagem, "erro_aws": aws_error_text(exc)},
    )


@router.post(
    "/input",
    response_model=GuardrailInputResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Valida o texto de entrada (reclamação) antes de entrar no pipeline",
)
def check_input(
    payload: GuardrailInputRequest,
    service: GuardrailService = Depends(get_guardrail_service),
    settings: Settings = Depends(get_settings),
) -> GuardrailInputResponse:
    try:
        result = service.check_input(payload.text)
    except BEDROCK_ERRORS as exc:
        raise _bedrock_unavailable(exc, settings) from exc
    logger.info("input blocked=%s reason=%s", result["blocked"], result.get("reason"))
    return GuardrailInputResponse(**result)


@router.post(
    "/output",
    response_model=GuardrailOutputResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Sanitiza o texto de saída gerado pelos agentes (remove PII, etc.)",
)
def sanitize_output(
    payload: GuardrailOutputRequest,
    service: GuardrailService = Depends(get_guardrail_service),
    settings: Settings = Depends(get_settings),
) -> GuardrailOutputResponse:
    try:
        text, meta = service.sanitize_output(payload.text, payload.field)
    except BEDROCK_ERRORS as exc:
        raise _bedrock_unavailable(exc, settings) from exc
    return GuardrailOutputResponse(sanitized_text=text, meta=meta)


@router.get("/blocked-message")
def blocked_message() -> dict:
    """Mensagem padrão a ser exibida ao cliente quando o input é bloqueado."""
    return {"message": BLOCKED_INPUT_MESSAGE}
