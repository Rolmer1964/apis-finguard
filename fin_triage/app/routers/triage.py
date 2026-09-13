"""Endpoint de triagem: classificação da reclamação via Claude Haiku."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..bedrock_errors import BEDROCK_ERRORS, aws_error_text, classify_bedrock_error
from ..config import Settings, get_settings
from ..dependencies import get_triage_service, verify_api_key
from ..models import TriageRequest, TriageResponse
from ..triage_service import TriageService

logger = logging.getLogger("fin_triage.api")

router = APIRouter(prefix="/v1", tags=["triage"])


def _bedrock_unavailable(exc: Exception, settings: Settings) -> HTTPException:
    """Converte um erro boto3 num HTTP 502 com causa específica e inequívoca.

    `detail` é um objeto `{codigo, mensagem, erro_aws}` — o `codigo`
    (ex.: BEDROCK_SEM_PERMISSAO, BEDROCK_SSO_EXPIRADO,
    BEDROCK_RECURSO_NAO_ENCONTRADO, BEDROCK_SEM_CONECTIVIDADE) permite ao
    chamador reagir sem parsear texto livre.
    """
    codigo, mensagem = classify_bedrock_error(
        exc,
        resource=settings.BEDROCK_MODEL_TRIAGE,
        region=settings.AWS_REGION,
        profile=settings.AWS_PROFILE,
    )
    logger.exception("Bedrock indisponível [%s]: %s", codigo, mensagem)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"codigo": codigo, "mensagem": mensagem, "erro_aws": aws_error_text(exc)},
    )


@router.post(
    "/triage",
    response_model=TriageResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Classifica a reclamação: categoria, produto, sentimento, urgência e resumo",
)
def triage(
    payload: TriageRequest,
    service: TriageService = Depends(get_triage_service),
    settings: Settings = Depends(get_settings),
) -> TriageResponse:
    try:
        result = service.run_triage(payload.text, payload.product_hint)
    except BEDROCK_ERRORS as exc:
        raise _bedrock_unavailable(exc, settings) from exc
    logger.info(
        "triage category=%s product=%s urgency=%s",
        result["category"], result["product"], result["urgency"],
    )
    return TriageResponse(**result)
