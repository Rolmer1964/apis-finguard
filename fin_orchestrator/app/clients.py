"""Clientes HTTP para as folhas. Uma função por chamada usada no pipeline.

Toda chamada:
- injeta `X-API-Key` se `API_KEY` estiver configurada;
- respeita `HTTP_TIMEOUT`;
- em resposta não-2xx, levanta `DownstreamError` carregando serviço, status e
  `detail` (dict `{codigo, mensagem, erro_aws}` das folhas de Bedrock, ou texto).
"""

from __future__ import annotations

import logging

import httpx

from .config import get_settings

logger = logging.getLogger("fin_orchestrator.clients")


class DownstreamError(Exception):
    def __init__(self, service: str, status_code: int, detail):
        self.service = service
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{service} -> HTTP {status_code}: {detail}")

    @property
    def codigo(self) -> str | None:
        if isinstance(self.detail, dict):
            return self.detail.get("codigo")
        return None

    @property
    def is_throttling(self) -> bool:
        if self.codigo == "BEDROCK_THROTTLING":
            return True
        return "throttl" in str(self.detail).lower()


def _headers() -> dict:
    key = get_settings().API_KEY
    return {"X-API-Key": key} if key else {}


def _request(method: str, url_key: str, service: str, path: str, *, json=None, params=None):
    s = get_settings()
    url = s.url_for(url_key) + path
    try:
        with httpx.Client(timeout=s.HTTP_TIMEOUT, headers=_headers()) as c:
            r = c.request(method, url, json=json, params=params)
    except httpx.RequestError as exc:
        raise DownstreamError(service, 503, f"sem resposta de {service} ({url}): {exc}") from exc
    if r.status_code // 100 == 2:
        if r.content and "application/json" in r.headers.get("content-type", ""):
            return r.json()
        return r.text
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        detail = r.text
    raise DownstreamError(service, r.status_code, detail)


# ── chamadas do pipeline ─────────────────────────────────────────────────────

def guardrail_input(text: str) -> dict:
    return _request("POST", "GUARDRAIL_URL", "fin_guardrail", "/v1/guardrail/input", json={"text": text})


def guardrail_output(text: str, field: str) -> dict:
    return _request(
        "POST", "GUARDRAIL_URL", "fin_guardrail", "/v1/guardrail/output",
        json={"text": text, "field": field},
    )


def triage(text: str, product_hint: str | None) -> dict:
    return _request(
        "POST", "TRIAGE_URL", "fin_triage", "/v1/triage",
        json={"text": text, "product_hint": product_hint},
    )


def rag_retrieve(query: str) -> dict:
    return _request("POST", "RAG_URL", "fin_rag", "/v1/rag/retrieve", json={"query": query})


def risk(text: str, triage_out: dict, policy_context: str | None, rag_chunks_count: int | None) -> dict:
    return _request(
        "POST", "RISK_URL", "fin_risk", "/v1/risk",
        json={
            "text": text,
            "triage": triage_out,
            "policy_context": policy_context,
            "rag_chunks_count": rag_chunks_count,
        },
    )


def consolidate(triage_out: dict, risk_out: dict, canal: str | None) -> dict:
    return _request(
        "POST", "CONSOLIDATE_URL", "fin_consolidate", "/v1/consolidate",
        json={"triage": triage_out, "risk": risk_out, "canal": canal},
    )


def post_trace(entry: dict) -> dict:
    return _request("POST", "TRACES_URL", "fin_traces", "/v1/traces", json=entry)


def create_report(results: list[dict], meta: dict) -> dict:
    return _request(
        "POST", "REPORT_WRITER_URL", "fin_report_writer", "/v1/reports",
        json={"results": results, "meta": meta},
    )


# ── healthcheck ──────────────────────────────────────────────────────────────

_DOWNSTREAMS = [
    ("GUARDRAIL_URL", "fin_guardrail"),
    ("TRIAGE_URL", "fin_triage"),
    ("RAG_URL", "fin_rag"),
    ("RISK_URL", "fin_risk"),
    ("CONSOLIDATE_URL", "fin_consolidate"),
    ("REPORT_WRITER_URL", "fin_report_writer"),
    ("TRACES_URL", "fin_traces"),
]


def ping_downstreams() -> dict:
    """Pinga `GET /health` de cada folha. Não levanta — devolve o mapa de estado."""
    s = get_settings()
    out: dict[str, dict] = {}
    with httpx.Client(timeout=min(s.HTTP_TIMEOUT, 5.0), headers=_headers()) as c:
        for key, name in _DOWNSTREAMS:
            url = s.url_for(key) + "/health"
            try:
                r = c.get(url)
                out[name] = {"ok": r.status_code == 200, "status_code": r.status_code, "url": s.url_for(key)}
            except httpx.RequestError as exc:
                out[name] = {"ok": False, "error": str(exc), "url": s.url_for(key)}
    return out
