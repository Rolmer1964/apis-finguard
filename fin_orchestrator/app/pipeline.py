"""Pipeline fim-a-fim de uma reclamação, orquestrando as folhas por HTTP.

Linearização do `graph.py` da finguard8 (fluxo é sequencial + 1 branch: se o
guardrail de entrada bloqueia, encerra). Cada etapa é uma chamada HTTP; o
tempo de cada uma entra em `timings_ms` (agora inclui latência de rede — ver
README). Ao final, registra a entrada no `fin_traces` (best-effort).
"""

from __future__ import annotations

import logging
import time
import uuid

from . import clients
from .profanity import mask as mask_profanity
from .timeutil import now_brt

logger = logging.getLogger("fin_orchestrator.pipeline")

_BLOCKED_FALLBACK_MSG = (
    "Não foi possível processar esta mensagem. Reformule sua reclamação sem "
    "linguagem ofensiva ou instruções ao sistema e tente novamente."
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _build_query(text: str, triage: dict) -> str:
    """Texto + dimensões da triagem — mesma heurística do `risk._build_query`."""
    bits = [text]
    for k in ("category", "product", "sentiment"):
        v = triage.get(k)
        if v:
            bits.append(str(v))
    return " ".join(bits)


def _preview(text: str) -> str:
    return (text[:70] + "…") if len(text) > 70 else text


def _post_trace(trace_id: str, text: str, result: dict, canal: str | None, timings: dict) -> None:
    entry = {
        "trace_id": trace_id,
        "timestamp": now_brt().strftime("%H:%M:%S"),
        "text_preview": _preview(text),
        "blocked": result.get("blocked", False),
        "category": result.get("category"),
        "urgency": result.get("urgency"),
        "risk_level": result.get("risk_level"),
        "product": result.get("product"),
        "canal": canal,
        "prazo_resposta": result.get("prazo_resposta"),
        "area_responsavel": result.get("area_responsavel"),
        "timings_ms": timings,
        "total_ms": sum(v for v in timings.values() if isinstance(v, (int, float))),
    }
    try:
        clients.post_trace(entry)
    except clients.DownstreamError as exc:
        logger.warning("[%s] falha ao registrar trace (seguindo): %s", trace_id, exc)


def blocked_record(rec_id: str, canal: str | None, r: dict) -> dict:
    """Normaliza um resultado bloqueado (`analyze_one` com `blocked=True`) no
    mesmo shape de um registro processado, para exibição uniforme (tabela de
    relatório + modal de detalhe do `fin_web` já sabem renderizar
    `category == "Bloqueado"`)."""
    return {
        "id": rec_id, "canal": canal,
        "trace_id": r.get("trace_id", ""),
        "texto_original": r.get("texto_original", ""),
        "timings_ms": r.get("timings_ms", {}),
        "block_reason": r.get("block_reason", ""),
        "category": "Bloqueado", "product": "—", "sentiment": "—", "urgency": "—",
        "summary": "[Entrada bloqueada pelo guardrail de proteção]",
        "risk_level": "—", "risk_justification": "",
    }


def analyze_one(
    text: str,
    product_hint: str | None = None,
    canal: str | None = None,
    record_id: str | None = None,
) -> dict:
    """Roda o pipeline completo e devolve o payload final (mesmo shape da finguard8)."""
    trace_id = record_id or uuid.uuid4().hex[:8]
    timings: dict[str, int] = {}
    logger.info("[%s] PIPELINE START canal=%s", trace_id, canal)

    # 1) Guardrail de entrada -------------------------------------------------
    t0 = _now_ms()
    gi = clients.guardrail_input(text)
    timings["guardrail_input"] = _now_ms() - t0

    if gi.get("blocked"):
        final = {
            "blocked": True,
            "message": gi.get("message") or _BLOCKED_FALLBACK_MSG,
            "texto_original": text,
        }
        if gi.get("block_reason"):
            final["block_reason"] = gi["block_reason"]
        result = {
            "trace_id": trace_id,
            "blocked": True,
            "triage": {},
            "risk": {},
            **final,
            "timings_ms": timings,
        }
        logger.info("[%s] PIPELINE END (bloqueado) reason=%s", trace_id, gi.get("reason"))
        _post_trace(trace_id, text, result, canal, timings)
        return result

    text = gi.get("sanitized_text") or text

    # 2) Triagem ------------------------------------------------------------
    t0 = _now_ms()
    triage_out = clients.triage(text, product_hint)
    timings["triage"] = _now_ms() - t0

    # 3) RAG: contexto da Política Interna --------------------------------
    t0 = _now_ms()
    rag = clients.rag_retrieve(_build_query(text, triage_out))
    timings["rag"] = _now_ms() - t0
    policy_context = rag.get("policy_context")
    rag_chunks_count = rag.get("count")

    # 4) Risco -------------------------------------------------------------
    t0 = _now_ms()
    risk_out = clients.risk(text, triage_out, policy_context, rag_chunks_count)
    timings["risk"] = _now_ms() - t0

    # 5) Consolidação (POL-SAC-001) -------------------------------------
    t0 = _now_ms()
    final = clients.consolidate(triage_out, risk_out, canal)
    final["texto_original"] = text
    timings["report"] = _now_ms() - t0

    # 6) Guardrail de saída ---------------------------------------------
    t0 = _now_ms()
    metas = []
    for field in ("texto_original", "summary", "risk_justification"):
        if final.get(field):
            resp = clients.guardrail_output(final[field], field)
            final[field] = resp.get("sanitized_text", final[field])
            meta = resp.get("meta") or {}
            if meta.get("bedrock_intervened") or meta.get("pii"):
                metas.append(meta)
    if metas:
        final["guardrail_output_meta"] = metas
    if final.get("texto_original"):
        original = final["texto_original"]
        final["texto_original"] = mask_profanity(original)
        if final["texto_original"] != original:
            final["profanity_masked"] = True
    timings["guardrail_output"] = _now_ms() - t0

    result = {
        "trace_id": trace_id,
        "blocked": False,
        "triage": triage_out,
        "risk": risk_out,
        **final,
        "timings_ms": timings,
    }
    logger.info(
        "[%s] PIPELINE END urgency=%s risk=%s timings=%s",
        trace_id, result.get("urgency"), result.get("risk_level"), timings,
    )
    _post_trace(trace_id, text, result, canal, timings)
    return result
