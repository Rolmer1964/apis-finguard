"""Healthcheck local + agregado das folhas."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..clients import ping_downstreams
from ..models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/health/downstream", summary="Pinga o /health de cada folha")
def health_downstream() -> JSONResponse:
    services = ping_downstreams()
    all_ok = all(v.get("ok") for v in services.values())
    return JSONResponse(
        {"status": "ok" if all_ok else "degraded", "services": services},
        status_code=200 if all_ok else 503,
    )
