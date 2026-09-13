"""Consolidação determinística POL-SAC-001.

Portado de `finguard8/app/src/agents/report.py` (função `consolidate` +
mapeamentos). Lógica pura, sem I/O: recebe os dicts de triagem e risco e
devolve o registro consolidado com SLA, área responsável e overrides de
canal regulatório aplicados.
"""

_SLA_POR_URGENCIA: dict[str, str] = {
    "Baixa":   "5 dias úteis",
    "Média":   "3 dias úteis",
    "Alta":    "24 horas",
    "Crítica": "4 horas",
}

_AREA_POR_PRODUTO: dict[str, str] = {
    "Cartão de Crédito": "Gerência de Cartões",
    "Conta Corrente":    "Gerência de Contas",
    "Empréstimo":        "Gerência de Crédito",
    "Investimentos":     "Gerência de Investimentos",
    "Seguros":           "Gerência de Seguros",
}

# Canais que exigem urgência CRÍTICA automática (POL-SAC-001 §4.3)
_CANAIS_CRITICOS: set[str] = {"Banco Central", "Procon", "Justiça"}

# Urgência mínima garantida por nível de risco
_URGENCIA_ORDEM: dict[str, int] = {"Crítica": 4, "Alta": 3, "Média": 2, "Baixa": 1}
_RISCO_URGENCIA_MINIMA: dict[str, str] = {"Crítico": "Alta"}

# Risco mínimo por canal regulatório — exposição independente do conteúdo (POL-SAC-001 §4.3)
_RISCO_ORDEM: dict[str, int] = {"Crítico": 4, "Alto": 3, "Médio": 2, "Baixo": 1}
_CANAIS_RISCO_MINIMO: dict[str, str] = {
    "Banco Central": "Alto",
    "Procon":        "Alto",
    "Justiça":       "Alto",
}


def consolidate(triage: dict, risk: dict, canal: str | None = None) -> dict:
    urgency    = triage.get("urgency")
    product    = triage.get("product")
    risk_level = risk.get("risk_level")
    risk_just  = risk.get("risk_justification") or ""

    # Override 1: canal regulatório → urgência CRÍTICA obrigatória (POL-SAC-001 §4.3)
    if canal in _CANAIS_CRITICOS and urgency != "Crítica":
        urgency = "Crítica"

    # Override 2: risco Crítico garante urgência mínima Alta (segunda linha de defesa)
    risco_min = _RISCO_URGENCIA_MINIMA.get(risk_level or "")
    if risco_min and _URGENCIA_ORDEM.get(urgency or "", 0) < _URGENCIA_ORDEM[risco_min]:
        urgency = risco_min

    # Override 3: canal regulatório → risco mínimo Alto por exposição regulatória (POL-SAC-001 §4.3)
    risk_level_original = None
    risco_canal_min = _CANAIS_RISCO_MINIMO.get(canal or "")
    if risco_canal_min and _RISCO_ORDEM.get(risk_level or "", 0) < _RISCO_ORDEM[risco_canal_min]:
        risk_level_original = risk_level
        nota = f" [Nível elevado de {risk_level} para {risco_canal_min} por canal regulatório ({canal}) — POL-SAC-001 §4.3]"
        risk_just  = (risk_just + nota).strip()
        risk_level = risco_canal_min

    out = {
        "category":           triage.get("category"),
        "product":            product,
        "sentiment":          triage.get("sentiment"),
        "urgency":            urgency,
        "summary":            triage.get("summary"),
        "prazo_resposta":     _SLA_POR_URGENCIA.get(urgency or ""),
        "area_responsavel":   _AREA_POR_PRODUTO.get(product or "", "Área de Suporte Geral"),
        "risk_level":         risk_level,
        "risk_justification": risk_just,
        "acoes_recomendadas": risk.get("acoes_recomendadas", []),
    }
    if risk_level_original:
        out["risk_level_original"] = risk_level_original
    return out
