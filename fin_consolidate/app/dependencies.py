"""Dependências compartilhadas entre os routers (injeção via FastAPI Depends)."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Autenticação simples por chave compartilhada.

    Se API_KEY não estiver configurada no .env, a verificação é ignorada
    (útil em desenvolvimento local).
    """
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida ou ausente.")
