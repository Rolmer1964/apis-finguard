"""Quebra o texto em chunks com overlap, preferindo limites de parágrafo.

Portado de `finguard8/app/src/rag/chunker.py` (verbatim).
"""

from __future__ import annotations

import re


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Divide `text` em pedaços ≤ max_chars tentando respeitar parágrafos.

    Estratégia:
      1. Splita por linha em branco (parágrafos).
      2. Acumula parágrafos até estourar max_chars.
      3. Parágrafos individuais maiores que max_chars são fatiados com overlap.
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current:
            chunks.append(current.strip())
            current = ""

    for p in paragraphs:
        if len(p) > max_chars:
            flush()
            step = max_chars - overlap
            for i in range(0, len(p), step):
                chunks.append(p[i:i + max_chars].strip())
            continue
        if not current:
            current = p
        elif len(current) + 2 + len(p) <= max_chars:
            current = current + "\n\n" + p
        else:
            flush()
            current = p
    flush()
    return [c for c in chunks if c]
