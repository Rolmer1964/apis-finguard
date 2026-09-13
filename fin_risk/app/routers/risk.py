"""Endpoint de risco: avaliação de risco + ações imediatas via Claude Sonnet."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..bedrock_errors import BEDROCK_ERRORS, aws_error_text, classify_bedrock_error
from ..config import Settings, get_settings
from ..dependencies import get_risk_service, verify_api_key
from ..models import RiskRequest, RiskResponse
from ..risk_service import RiskService

logger = logging.getLogger("fin_risk.api")

router = APIRouter(prefix="/v1", tags=["risk"])


def _bedrock_unavailable(exc: Exception, settings: Settings) -> HTTPException:
    """Converte um erro boto3 num HTTP 502 com causa específica e inequívoca.

    `detail` é um objeto `{codigo, mensagem, erro_aws}` — o `codigo`
    (ex.: BEDROCK_SEM_PERMISSAO, BEDROCK_SSO_EXPIRADO,
    BEDROCK_RECURSO_NAO_ENCONTRADO, BEDROCK_SEM_CONECTIVIDADE) permite ao
    chamador reagir sem parsear texto livre.
    """
    codigo, mensagem = classify_bedrock_error(
        exc,
        resource=settings.BEDROCK_MODEL_RISK,
        region=settings.AWS_REGION,
        profile=settings.AWS_PROFILE,
    )
    logger.exception("Bedrock indisponível [%s]: %s", codigo, mensagem)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"codigo": codigo, "mensagem": mensagem, "erro_aws": aws_error_text(exc)},
    )


@router.post(
    "/risk",
    response_model=RiskResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Avalia o risco da reclamação e gera as ações imediatas (POL-SAC-001 §2/§3)",
)
def risk(
    payload: RiskRequest,
    service: RiskService = Depends(get_risk_service),
    settings: Settings = Depends(get_settings),
) -> RiskResponse:
    try:
        result = service.run_risk(
            payload.text,
            payload.triage.model_dump(),
            payload.policy_context,
            payload.rag_chunks_count,
        )
    except BEDROCK_ERRORS as exc:
        raise _bedrock_unavailable(exc, settings) from exc
    logger.info(
        "risk risk_level=%s rag_chunks_used=%s acoes=%d",
        result["risk_level"], result["rag_chunks_used"], len(result["acoes_recomendadas"]),
    )
    return RiskResponse(**result)
