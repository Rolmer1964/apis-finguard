"""Healthcheck local. NÃO pinga o orquestrador (isto é responsabilidade do
`GET {ORCH}/health/downstream`)."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()
