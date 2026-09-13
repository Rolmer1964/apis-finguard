"""Contexto do log de execução (para a tela de traces do `fin_web`).

Portado de `finguard8/app/src/main.py::_build_traces_context` + `_LEVEL_STYLE`.
Devolve o mesmo dict que o monólito passava ao `traces.html.j2`; aqui vira o
corpo JSON de `GET /v1/traces`. O `fin_web` renderiza o template.
"""

from .helpers import bar_width_px, compute_stats, pill_html

_LEVEL_STYLE = {
    "crít": "color:#991b1b;font-weight:600",
    "alt": "color:#9a3412;font-weight:600",
    "méd": "color:#92400e",
    "med": "color:#92400e",
    "baix": "color:#065f46",
}


def build_traces_context(data: list[dict]) -> dict:
    series: dict[str, list[float]] = {"total_ms": [], "triage": [], "risk": [], "report": []}
    for t in data:
        tm = t.get("timings_ms", {})
        series["total_ms"].append(float(t.get("total_ms") or 0))
        if not t.get("blocked"):
            series["triage"].append(float(tm.get("triage") or 0))
            series["risk"].append(float(tm.get("risk") or 0))
            series["report"].append(float(tm.get("report") or 0))

    st = {k: compute_stats(v) for k, v in series.items()}

    traces_display = []
    for t in data:
        tm = t.get("timings_ms", {})
        t_ms = int(tm.get("triage", 0) or 0)
        r_ms = int(tm.get("risk", 0) or 0)
        rp_ms = int(tm.get("report", 0) or 0)
        gi_ms = int(tm.get("guardrail_input", 0) or 0)
        pipeline = t_ms + r_ms + rp_ms
        total_e2e = int(t.get("total_ms") or gi_ms + pipeline)
        traces_display.append({
            **t,
            "t_ms": t_ms,
            "r_ms": r_ms,
            "rp_ms": rp_ms,
            "gi_ms": gi_ms,
            "total_display": total_e2e,
            "bar_triage": bar_width_px(t_ms, pipeline),
            "bar_risk": bar_width_px(r_ms, pipeline),
            "bar_report": bar_width_px(rp_ms, pipeline),
            "urgency_html": pill_html(t.get("urgency"), _LEVEL_STYLE),
            "risk_level_html": pill_html(t.get("risk_level"), _LEVEL_STYLE),
        })

    return {
        "count": len(data),
        "st": st,
        "has_data": bool(data),
        "traces": traces_display,
    }
