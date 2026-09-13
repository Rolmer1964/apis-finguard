"""Lê arquivos da pasta de documentos e extrai texto.

Suporta: .pdf (via pypdf), .md / .markdown / .txt (texto direto).
Portado de `finguard8/app/src/rag/loader.py` (verbatim).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("fin_rag.loader")

SUPPORTED_EXT = {".pdf", ".md", ".markdown", ".txt"}


@dataclass(frozen=True)
class Document:
    relpath: str        # caminho relativo à raiz dos docs (id estável entre runs)
    text: str
    sha256: str


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning("falha extraindo página de %s: %s", path.name, exc)
    return "\n".join(parts)


def _extract_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_documents(root: str | Path) -> list[Document]:
    """Anda na pasta `root` e devolve um Document por arquivo suportado."""
    base = Path(root)
    if not base.exists():
        logger.warning("pasta de docs não encontrada: %s", base)
        return []

    docs: list[Document] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXT:
            continue
        relpath = str(path.relative_to(base)).replace("\\", "/")
        raw_bytes = path.read_bytes()
        try:
            if path.suffix.lower() == ".pdf":
                text = _extract_pdf(path)
            else:
                text = _extract_text(path)
        except Exception as exc:
            logger.exception("falha lendo %s: %s", relpath, exc)
            continue
        if not text.strip():
            logger.warning("documento vazio (sem texto extraído): %s", relpath)
            continue
        docs.append(Document(relpath=relpath, text=text, sha256=_hash(raw_bytes)))
        logger.info("carregado %s (%d chars, sha=%s)", relpath, len(text), _hash(raw_bytes)[:8])
    return docs
