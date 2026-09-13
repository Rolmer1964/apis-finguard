"""Fixtures compartilhadas dos testes.

O modelo de embedding real nunca é carregado: `RagService._embed_one` (única
chamada que usa o modelo local) é substituído por um stub determinístico. O
índice FAISS vai para um diretório temporário, limpo antes de cada teste.
Probe e ingestão de startup ficam desligados.
"""

import hashlib
import os
import shutil
import tempfile

import numpy as np

_TMP = tempfile.mkdtemp(prefix="fin_rag_test_")
os.environ["RAG_INDEX_DIR"] = os.path.join(_TMP, "index")
os.environ["RAG_DOCS_DIR"] = os.path.join(_TMP, "docs")
os.environ["EMBED_DIM"] = "32"
os.environ["RAG_CHUNK_CHARS"] = "200"
os.environ["RAG_CHUNK_OVERLAP"] = "20"
os.environ["RAG_TOP_K"] = "4"
os.environ["PROBE_ON_STARTUP"] = "false"
os.environ["INGEST_ON_STARTUP"] = "false"
os.makedirs(os.environ["RAG_DOCS_DIR"], exist_ok=True)
os.makedirs(os.environ["RAG_INDEX_DIR"], exist_ok=True)

import pytest  # noqa: E402

from app.index_state import reload_store  # noqa: E402
from app.rag_service import RagService  # noqa: E402

DOCS_DIR = os.environ["RAG_DOCS_DIR"]
INDEX_DIR = os.environ["RAG_INDEX_DIR"]


def _fake_embed_one(self, text: str) -> np.ndarray:
    """Vetor normalizado determinístico: mesmo texto -> mesmo vetor (score 1.0)."""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(self._settings.EMBED_DIM).astype("float32")
    n = float(np.linalg.norm(v))
    return v / (n if n else 1.0)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setattr(RagService, "_embed_one", _fake_embed_one)
    # índice e docs limpos antes de cada teste
    for d in (INDEX_DIR, DOCS_DIR):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
    reload_store()
    yield
    reload_store()


def write_doc(name: str, text: str) -> None:
    with open(os.path.join(DOCS_DIR, name), "w", encoding="utf-8") as f:
        f.write(text)
