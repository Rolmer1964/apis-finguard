"""Endpoint de consolidação determinística (POL-SAC-001)."""

import logging

from fastapi import APIRouter, Depends

from ..consolidation import consolidate
from ..dependencies import verify_api_key
from ..models import ConsolidateRequest, ConsolidateResponse

logger = logging.getLogger("fin_consolidate.api")

router = APIRouter(prefix="/v1", tags=["consolidate"])


@router.post(
    "/consolidate",
    response_model=ConsolidateResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Aplica as regras POL-SAC-001 sobre triagem + risco",
)
def consolidate_endpoint(payload: ConsolidateRequest) -> ConsolidateResponse:
    result = consolidate(
        payload.triage.model_dump(),
        payload.risk.model_dump(),
        canal=payload.canal,
    )
    logger.info(
        "consolidate canal=%s urgency=%s risk=%s area=%s override=%s",
        payload.canal,
        result["urgency"],
        result["risk_level"],
        result["area_responsavel"],
        "risk_level_original" in result,
    )
    return ConsolidateResponse(**result)
