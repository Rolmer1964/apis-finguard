"""Painel decisório + recomposição do log a partir de relatórios.

Portado de `finguard8/app/src/main.py`: `_norm_urgency`, `_norm_risk`,
`_URGENCY_TO_PRAZO`, `decisorio_stats`, e a lógica de `/traces/recompose` /
`_recompose_all_traces` (aqui recebe a lista `results` no corpo, em vez de ler
arquivos de `OUTPUT_DIR`).
"""

from .trace_store import inject_trace, sum_timings

URGENCY_LEVELS = ["Crítica", "Alta", "Média", "Baixa"]
RISK_LEVELS = ["Crítico", "Alto", "Médio", "Baixo"]

_URGENCY_TO_PRAZO = {
    "Crítica": "4 horas",
    "Alta": "24 horas",
    "Média": "3 dias úteis",
    "Baixa": "5 dias úteis",
}


def _norm_urgency(u: str | None) -> str | None:
    s = (u or "").lower()
    if "crít" in s or "crit" in s:
        return "Crítica"
    if "alt" in s:
        return "Alta"
    if "méd" in s or "med" in s:
        return "Média"
    if "baix" in s:
        return "Baixa"
    return None


def _norm_risk(r: str | None) -> str | None:
    s = (r or "").lower()
    if "crít" in s or "crit" in s:
        return "Crítico"
    if "alt" in s:
        return "Alto"
    if "méd" in s or "med" in s:
        return "Médio"
    if "baix" in s:
        return "Baixo"
    return None


def build_decisorio_stats(data: list[dict]) -> dict:
    """Agrega o trace store para o Painel Decisório (mesma saída do monólito)."""
    non_blocked = [t for t in data if not t.get("blocked")]

    total = len(data)
    bloqueados = total - len(non_blocked)

    urgency_map: dict[str, int] = {}
    risk_map: dict[str, int] = {}
    area_map: dict[str, int] = {}
    prazo_map: dict[str, int] = {}
    canal_map: dict[str, dict] = {}

    matrix = {u: {r: 0 for r in RISK_LEVELS} for u in URGENCY_LEVELS}

    for t in data:
        c = t.get("canal") or "Não informado"
        if c not in canal_map:
            canal_map[c] = {"total": 0, "critica": 0}
        canal_map[c]["total"] += 1
        if _norm_urgency(t.get("urgency")) == "Crítica":
            canal_map[c]["critica"] += 1

    for t in non_blocked:
        u_norm = _norm_urgency(t.get("urgency"))
        r_norm = _norm_risk(t.get("risk_level"))

        u_key = u_norm or t.get("urgency") or "Não informado"
        r_key = r_norm or t.get("risk_level") or "Não informado"
        urgency_map[u_key] = urgency_map.get(u_key, 0) + 1
        risk_map[r_key] = risk_map.get(r_key, 0) + 1

        area = t.get("area_responsavel") or "Não informado"
        area_map[area] = area_map.get(area, 0) + 1

        prazo = t.get("prazo_resposta") or _URGENCY_TO_PRAZO.get(u_norm or "")
        if prazo:
            prazo_map[prazo] = prazo_map.get(prazo, 0) + 1

        if u_norm and r_norm:
            matrix[u_norm][r_norm] += 1

    timings_total = [float(t.get("total_ms") or 0) for t in data if t.get("total_ms")]
    avg_total_ms = round(sum(timings_total) / len(timings_total)) if timings_total else 0

    return {
        "total": total,
        "bloqueados": bloqueados,
        "processados": len(non_blocked),
        "avg_total_ms": avg_total_ms,
        "urgency": urgency_map,
        "risk": risk_map,
        "canais": canal_map,
        "areas": area_map,
        "prazos": prazo_map,
        "matrix": matrix,
        "urgency_levels": URGENCY_LEVELS,
        "risk_levels": RISK_LEVELS,
    }


def recompose_from_results(results: list[dict]) -> int:
    """Reconstrói entradas de log a partir do `results` de um relatório batch.

    Injeta na mesma ordem do monólito (mais antigo primeiro → mais recente no
    topo do deque). Devolve quantas entradas foram injetadas.
    """
    for item in reversed(results):
        texto = item.get("texto_original", "") or ""
        tm = item.get("timings_ms", {})
        inject_trace({
            "trace_id": item.get("id", "?"),
            "timestamp": item.get("timestamp", ""),
            "text_preview": (texto[:70] + "…") if len(texto) > 70 else texto,
            "blocked": item.get("blocked", False),
            "category": item.get("category"),
            "urgency": item.get("urgency"),
            "risk_level": item.get("risk_level"),
            "product": item.get("product"),
            "canal": item.get("canal"),
            "prazo_resposta": item.get("prazo_resposta"),
            "area_responsavel": item.get("area_responsavel"),
            "timings_ms": tm,
            "total_ms": sum_timings(tm),
        })
    return len(results)
