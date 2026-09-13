"""Estatísticas e utilidades de layout do log/painel.

Portado de `finguard8/app/src/helpers.py` (mesma cópia do `fin_report_writer`).
Só o que o `fin_traces` usa: `compute_stats`, `_percentile`, `pill_html`,
`bar_width_px`. (`count_output_files` e `rag_vector_count` ficam de fora.)
"""

import math
import statistics


def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[max(0, math.ceil(p * len(s)) - 1)]


def compute_stats(vals: list[float]) -> dict:
    if not vals:
        return {"mean": 0, "median": 0, "stdev": 0, "cv": 0.0, "p95": 0, "p99": 0}
    mean = statistics.mean(vals)
    stdev = statistics.stdev(vals) if len(vals) > 1 else 0
    return {
        "mean": round(mean),
        "stdev": round(stdev),
        "cv": round(stdev / mean * 100, 1) if mean else 0.0,
        "median": round(statistics.median(vals)),
        "p95": round(_percentile(vals, 0.95)),
        "p99": round(_percentile(vals, 0.99)),
    }


def pill_html(value: str | None, mapping: dict) -> str:
    v = (value or "").lower()
    for prefix, style in mapping.items():
        if v.startswith(prefix):
            return f'<span style="{style}">{value}</span>'
    return value or "—"


def bar_width_px(ms: float, total: float) -> str:
    return f"{max(int(ms / max(total, 1) * 80), 1)}px"
