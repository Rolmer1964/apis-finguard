"""Estado de processo do fin_rag: o índice em memória (singleton) e o estado
da ingestão em background.

- `get_store()` devolve um `VectorStore` carregado uma vez e reutilizado entre
  requests (retrieval é read-only). `reload_store()` força recarga do disco
  após uma ingestão ou reset.
- `get_ingest_state()` / `set_ingest_state()` guardam o progresso da ingestão
  disparada por `POST /v1/rag/ingest` (roda numa thread).
"""

import threading
from functools import lru_cache

from .config import Settings
from .rag.store import VectorStore


@lru_cache(maxsize=1)
def _cached_store(dim: int, index_dir: str) -> VectorStore:
    store = VectorStore(dim=dim, index_dir=index_dir)
    store.load()
    return store


def get_store(settings: Settings) -> VectorStore:
    return _cached_store(settings.EMBED_DIM, settings.RAG_INDEX_DIR)


def reload_store() -> None:
    _cached_store.cache_clear()


_ingest_lock = threading.Lock()
_ingest_state: dict = {"status": "idle", "stats": None, "error": None}


def get_ingest_state() -> dict:
    with _ingest_lock:
        return dict(_ingest_state)


def set_ingest_state(status: str, stats: dict | None, error: str | None) -> None:
    with _ingest_lock:
        _ingest_state.update(status=status, stats=stats, error=error)
