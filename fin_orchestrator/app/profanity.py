"""Filtro local de palavrões — `mask()` substitui por "***".

Portado de `finguard8/app/src/profanity.py` (verbatim).
"""

import re

PALAVROES = [
    # ---------- Profanidade clássica ----------
    r"\bporra\b", r"\bporr[ai]nh[ao]s?\b",
    r"\bmerd[ao]s?\b", r"\bmerdinhas?\b",
    r"\bcaralh[ao]s?\b", r"\bcaralhada\b",
    r"\bbost[ao]s?\b", r"\bbostinhas?\b",
    r"\bdesgraç[ao]s?\b", r"\bdesgraçad[ao]s?\b",
    r"\binfern[ao]\b", r"\bdiab[ao]s?\b",

    # ---------- Sexual / pesado ----------
    r"\bcuz[ãa]o\b", r"\bcuzinhos?\b", r"\bcus?\b",
    r"\bbu?cetas?\b", r"\bxoxotas?\b",
    r"\bpirocas?\b", r"\bpic[ao]s?\b", r"\bpint[ao]\b",
    r"\bfod[ae]r?\b", r"\bfodid[ao]s?\b", r"\bfodass?e\b", r"\bfoda[- ]se\b",
    r"\bput[ao]s?\b", r"\bputari[ao]\b", r"\bputeir[ao]\b",
    r"\bputa\s+que\s+(o\s+)?pariu\b",
    r"\barromb[ao]d[ao]s?\b",
    r"\bcorn[ao]s?\b", r"\bchifrud[ao]s?\b",

    # ---------- Insultos ----------
    r"\bidiotas?\b", r"\bidiotices?\b",
    r"\bimbecis?\b", r"\bimbeci[sl]\b",
    r"\bburr[ao]s?\b", r"\bburrices?\b",
    r"\botári[ao]s?\b", r"\botári[ao]ç[ao]s?\b",
    r"\bbabacas?\b", r"\btrouxas?\b", r"\bpanacas?\b",
    r"\bcretin[ao]s?\b", r"\bcanalhas?\b",
    r"\bsafad[ao]s?\b", r"\bvagabund[ao]s?\b",
    r"\bescrot[ao]s?\b", r"\bbest[ao]s?\b",
    r"\bnojent[ao]s?\b", r"\blix[ao]s?\b",  # "esse banco é um lixo"
    r"\bjument[ao]s?\b", r"\btapad[ao]s?\b",

    # ---------- Abreviações / internetês ----------
    r"\bfdps?\b",          # filho da puta / FDPs
    r"\bpqp\b",            # puta que pariu
    r"\bvsf\b", r"\bvtnc\b", r"\btnc\b",  # vai se foder / tomar no cu
    r"\bkrl\b", r"\bporrr+a\b",           # "porraaaa"
    r"\bfds\b",            # foda-se (cuidado: também é "fim de semana")

    # ---------- Versões censuradas com asteriscos ----------
    r"\bp[\*\.@#]+r+a\b",
    r"\bc[\*\.@#]+r[\*\.@#]+lh[ao]\b",
    r"\bm[\*\.@#]+rd[ao]\b",
    r"\bf[\*\.@#]+d[ao]\b",
    r"\bfdp[\*\.@#]+\b",
]
_RE = re.compile("|".join(PALAVROES), re.IGNORECASE)


def mask(text: str | None) -> str:
    if not text:
        return text or ""
    return _RE.sub("***", text)
