"""Lógica de RAG (embedding, retrieval, ingestão), adaptada para uso como
serviço injetável.

Portado de `finguard8/app/src/rag/{embedder,retriever,ingest}.py`. O embedding
roda localmente (`app/embedder.py`, sentence-transformers) — sem chamada
externa, sem credencial. O resto é FAISS + disco.
"""

import logging
from pathlib import Path

import numpy as np

from . import embedder
from .config import Settings
from .index_state import get_store, reload_store, set_ingest_state
from .rag.chunker import chunk_text
from .rag.loader import load_documents
from .rag.store import RetrievedChunk, VectorStore

logger = logging.getLogger("fin_rag.service")

EMPTY_POLICY_CONTEXT = "(nenhum trecho da política interna disponível — índice vazio)"


class RagService:
    """Encapsula embedding local (sentence-transformers) + índice FAISS local.

    Uma instância é criada por request (via Depends no FastAPI), recebendo as
    Settings já resolvidas.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── seam testável: única chamada que carrega/usa o modelo local ──────
    def _embed_one(self, text: str) -> np.ndarray:
        return embedder.embed_one(self._settings.EMBED_MODEL_NAME, text)

    def _embed_many(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self._settings.EMBED_DIM), dtype="float32")
        for i, t in enumerate(texts):
            out[i] = self._embed_one(t)
            if (i + 1) % 25 == 0:
                logger.info("embed %d/%d", i + 1, len(texts))
        return out

    def ping(self) -> None:
        """1 embedding local só para garantir que o modelo carregou (usado no startup)."""
        self._embed_one("fin_rag: verificacao de conectividade no startup")

    # ── retrieval ───────────────────────────────────────────────────────
    def retrieve(self, query: str, k: int | None = None) -> tuple[list[RetrievedChunk], str]:
        k = k or self._settings.RAG_TOP_K
        store = get_store(self._settings)
        if store.total_vectors == 0:
            return [], EMPTY_POLICY_CONTEXT
        qvec = self._embed_one(query)
        chunks = store.search(qvec, k=k)
        return chunks, self.format_for_prompt(chunks)

    @staticmethod
    def format_for_prompt(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return EMPTY_POLICY_CONTEXT
        parts = [
            f"[{i}] Fonte: {c.source} (trecho {c.chunk_idx})\n{c.text}"
            for i, c in enumerate(chunks, 1)
        ]
        return "Trechos relevantes da Política Interna:\n\n" + "\n\n---\n\n".join(parts)

    # ── ingestão ────────────────────────────────────────────────────────
    def ingest(self) -> dict:
        """Sincroniza o índice com o estado atual de RAG_DOCS_DIR (incremental
        por hash). Recarrega o índice em memória ao final."""
        store = VectorStore(dim=self._settings.EMBED_DIM, index_dir=self._settings.RAG_INDEX_DIR)
        store.load()

        docs = load_documents(self._settings.RAG_DOCS_DIR)
        on_disk = {d.relpath: d for d in docs}
        known = store.known_files()

        new_paths = sorted(set(on_disk) - known)
        removed_paths = sorted(known - set(on_disk))
        changed_paths = sorted(p for p in (set(on_disk) & known) if store.file_hash(p) != on_disk[p].sha256)
        skipped_paths = sorted(p for p in (set(on_disk) & known) if store.file_hash(p) == on_disk[p].sha256)

        chunks_removed = 0
        for p in removed_paths + changed_paths:
            before = store.total_vectors
            store.remove_file(p)
            chunks_removed += before - store.total_vectors

        chunks_added = 0
        for p in new_paths + changed_paths:
            doc = on_disk[p]
            chunks = chunk_text(
                doc.text,
                max_chars=self._settings.RAG_CHUNK_CHARS,
                overlap=self._settings.RAG_CHUNK_OVERLAP,
            )
            if not chunks:
                logger.warning("nenhum chunk gerado para %s; pulando", p)
                continue
            logger.info("embedando %d chunks de %s", len(chunks), p)
            vectors = self._embed_many(chunks)
            store.add_file(p, doc.sha256, chunks, vectors)
            chunks_added += len(chunks)

        store.save()
        reload_store()

        stats = {
            "new": new_paths,
            "changed": changed_paths,
            "removed": removed_paths,
            "skipped": skipped_paths,
            "chunks_added": chunks_added,
            "chunks_removed": chunks_removed,
            "total_vectors_after": store.total_vectors,
        }
        logger.info("ingestão concluída: %s", stats)
        return stats

    def run_ingest_bg(self) -> None:
        """Wrapper de `ingest()` que publica o progresso em `index_state`."""
        set_ingest_state("running", None, None)
        try:
            stats = self.ingest()
            set_ingest_state("done", stats, None)
        except Exception as exc:  # noqa: BLE001 - queremos registrar qualquer falha
            logger.exception("RAG: falha na ingestão")
            set_ingest_state("error", None, str(exc))

    # ── introspecção / manutenção ───────────────────────────────────────
    def stats(self) -> dict:
        store = get_store(self._settings)
        files = [
            {"path": p, "chunks": len(v.get("chunk_ids", [])), "hash": (v.get("hash") or "")[:12]}
            for p, v in store.manifest.get("files", {}).items()
        ]
        return {
            "total_vectors": store.total_vectors,
            "files": files,
            "updated_at": store.manifest.get("updated_at"),
        }

    def reset(self) -> dict:
        """Apaga os arquivos do índice (regenerável via ingestão)."""
        removed = 0
        for f in Path(self._settings.RAG_INDEX_DIR).glob("*"):
            if f.is_file():
                f.unlink()
                removed += 1
        reload_store()
        logger.info("índice resetado: %d arquivo(s) removido(s)", removed)
        return {"removed_index_files": removed, "status": "ok"}
