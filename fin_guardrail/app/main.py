"""FinGuard - Guardrail API.

Serviço standalone (nó de guardrail do grafo do FinGuard) que expõe:
- POST /v1/guardrail/input   -> valida/bloqueia a reclamação recebida
- POST /v1/guardrail/output  -> sanitiza a saída gerada pelos agentes
- GET  /health               -> healthcheck

Bootstrap apenas: configuração de logging, validação das settings, probe de
conectividade com o Bedrock, criação do app e registro dos routers. A lógica
de cada endpoint vive em `app/routers/`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from .bedrock_errors import BEDROCK_ERRORS, classify_bedrock_error
from .config import get_settings
from .guardrail_service import GuardrailService
from .logging_config import setup_logging
from .routers import guardrail, health

setup_logging()
logger = logging.getLogger("fin_guardrail.api")

# Falha alto no boot se GUARDRAIL_ID não estiver configurado — a API chama o
# Bedrock de verdade e não sobe sem guardrail.
_settings = get_settings()
logger.info(
    "Bedrock guardrail: id=%s versao=%s regiao=%s (output_id=%s)",
    _settings.GUARDRAIL_ID,
    _settings.GUARDRAIL_VERSION,
    _settings.AWS_REGION,
    _settings.GUARDRAIL_ID_OUTPUT or "(mesmo do input)",
)


def _probe_bedrock() -> None:
    """Faz uma chamada real ao Bedrock (`apply_guardrail`) no startup.

    A API só funciona com conectividade real ao Amazon Bedrock — não há
    fallback local. Se o probe falhar, o startup é **abortado** com
    `RuntimeError: [CODIGO] mensagem`, onde CODIGO identifica a causa exata
    (ver `app/bedrock_errors.py`): BEDROCK_SEM_CREDENCIAIS,
    BEDROCK_SSO_EXPIRADO, BEDROCK_SEM_PERMISSAO,
    BEDROCK_GUARDRAIL_NAO_ENCONTRADO, BEDROCK_SEM_CONECTIVIDADE, etc.
    """
    settings = get_settings()
    try:
        GuardrailService(settings).ping()
    except BEDROCK_ERRORS as exc:
        codigo, mensagem = classify_bedrock_error(
            exc,
            guardrail_id=settings.GUARDRAIL_ID,
            region=settings.AWS_REGION,
            profile=settings.AWS_PROFILE,
        )
        logger.error("Startup abortado [%s]: %s", codigo, mensagem)
        raise RuntimeError(f"[{codigo}] {mensagem}") from exc
    logger.info("Conectividade com o Amazon Bedrock verificada — API pronta.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _probe_bedrock()
    yield


app = FastAPI(
    title="FinGuard - Guardrail API",
    description=(
        "Serviço responsável por validar entradas e sanitizar saídas do "
        "pipeline FinGuard usando Amazon Bedrock Guardrails."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(guardrail.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Navegadores pedem /favicon.ico ao abrir /docs. É uma API, não há ícone —
    responde 204 (sem conteúdo) para não poluir o log com 404."""
    return Response(status_code=204)
