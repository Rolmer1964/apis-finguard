"""Cliente HTTP para o `fin_orchestrator` — a única origem de dados do fin_web.

Três formas de uso:
- `get_json(path)` / `post_json(path, ...)` — quando o fin_web precisa do corpo
  já desserializado (páginas SSR, ações que inspecionam a resposta);
- `forward(request, path)` — repasse 1:1 (status, corpo, content-type) de uma
  chamada do browser para o orquestrador (proxies de leitura/escrita finos).

Falha de transporte (orquestrador fora) vira `OrchestratorError` com status 502;
resposta não-2xx do orquestrador é propagada com o status e o corpo originais.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import Request
from fastapi.responses import Response

from .config import get_settings

logger = logging.getLogger("fin_web.orchestrator")


class OrchestratorError(Exception):
    """O orquestrador respondeu não-2xx ou não respondeu."""

    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"orquestrador -> HTTP {status_code}: {detail}")


def _headers(extra: dict | None = None) -> dict:
    h = dict(extra or {})
    key = get_settings().API_KEY
    if key:
        h["X-API-Key"] = key
    return h


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(base_url=s.orch, timeout=s.HTTP_TIMEOUT)


def _unwrap(r: httpx.Response):
    if r.status_code // 100 == 2:
        ctype = r.headers.get("content-type", "")
        if r.content and "application/json" in ctype:
            return r.json()
        return r.text
    try:
        detail = r.json().get("detail", r.json())
    except Exception:
        detail = r.text
    raise OrchestratorError(r.status_code, detail)


def get_json(path: str, params: dict | None = None):
    try:
        with _client() as c:
            r = c.get(path, params=params, headers=_headers())
    except httpx.RequestError as exc:
        raise OrchestratorError(502, f"orquestrador indisponível ({path}): {exc}") from exc
    return _unwrap(r)


def post_json(path: str, *, json=None, params: dict | None = None):
    try:
        with _client() as c:
            r = c.post(path, json=json, params=params, headers=_headers())
    except httpx.RequestError as exc:
        raise OrchestratorError(502, f"orquestrador indisponível ({path}): {exc}") from exc
    return _unwrap(r)


async def forward(request: Request, path: str, *, params: dict | None = None) -> Response:
    """Repassa a requisição do browser para o orquestrador, 1:1."""
    s = get_settings()
    body = await request.body()
    headers = _headers()
    if request.headers.get("content-type"):
        headers["content-type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(base_url=s.orch, timeout=s.HTTP_TIMEOUT) as c:
            r = await c.request(
                request.method, path,
                params=params if params is not None else request.query_params,
                content=body or None, headers=headers,
            )
    except httpx.RequestError as exc:
        logger.warning("forward %s %s -> sem resposta: %s", request.method, path, exc)
        return Response(
            content=f'{{"detail":"orquestrador indisponível: {exc}"}}',
            status_code=502, media_type="application/json",
        )
    passthru = {}
    if r.headers.get("content-disposition"):
        passthru["content-disposition"] = r.headers["content-disposition"]
    return Response(
        content=r.content, status_code=r.status_code,
        media_type=r.headers.get("content-type"), headers=passthru,
    )
