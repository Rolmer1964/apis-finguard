"""Persistência do índice FAISS + manifest com metadados de chunks e arquivos.

Portado de `finguard8/app/src/rag/store.py`. Única mudança: `now_brt` vem de
`app/timeutil.py` em vez de `settings.py`.

Layout em disco:
    {RAG_INDEX_DIR}/
      faiss.bin           # IndexIDMap2(IndexFlatIP) com vetores normalizados
      manifest.json       # {next_id, files: {relpath: {hash, chunk_ids}}, chunks: {id: {file, idx, text}}}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from ..timeutil import now_brt

logger = logging.getLogger("fin_rag.store")


@dataclass
class RetrievedChunk:
    chunk_id: int
    score: float
    text: str
    source: str  # caminho relativo do arquivo
    chunk_idx: int


class VectorStore:
    """FAISS IndexIDMap2 sobre IndexFlatIP (cosine se vetores normalizados)."""

    def __init__(self, dim: int, index_dir: str | Path):
        self.dim = dim
        self.dir = Path(index_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.faiss_path = self.dir / "faiss.bin"
        self.manifest_path = self.dir / "manifest.json"
        self.index: faiss.Index | None = None
        self.manifest: dict = {"next_id": 0, "files": {}, "chunks": {}, "updated_at": None}

    # ---------- carga / salvamento ----------
    def load(self) -> None:
        if self.manifest_path.exists():
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if self.faiss_path.exists():
            self.index = faiss.read_index(str(self.faiss_path))
        else:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

    def save(self) -> None:
        self.manifest["updated_at"] = now_brt().isoformat(timespec="seconds")
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.index is not None:
            faiss.write_index(self.index, str(self.faiss_path))
        logger.info("salvou índice (%d vetores) e manifest em %s", self.index.ntotal if self.index else 0, self.dir)

    # ---------- mutações ----------
    def remove_file(self, relpath: str) -> None:
        meta = self.manifest["files"].pop(relpath, None)
        if not meta:
            return
        ids = meta.get("chunk_ids", [])
        if ids:
            self.index.remove_ids(np.array(ids, dtype="int64"))
            for cid in ids:
                self.manifest["chunks"].pop(str(cid), None)
            logger.info("removidos %d chunks de %s", len(ids), relpath)

    def add_file(self, relpath: str, file_hash: str, chunks: list[str], vectors: np.ndarray) -> None:
        if vectors.shape[0] != len(chunks):
            raise ValueError("número de vetores != número de chunks")
        next_id = self.manifest["next_id"]
        ids = list(range(next_id, next_id + len(chunks)))
        self.index.add_with_ids(vectors.astype("float32"), np.array(ids, dtype="int64"))
        for cid, idx, text in zip(ids, range(len(chunks)), chunks):
            self.manifest["chunks"][str(cid)] = {"file": relpath, "idx": idx, "text": text}
        self.manifest["files"][relpath] = {
            "hash": file_hash,
            "chunk_ids": ids,
            "ingested_at": now_brt().isoformat(timespec="seconds"),
        }
        self.manifest["next_id"] = next_id + len(chunks)
        logger.info("adicionados %d chunks de %s (ids %d..%d)", len(chunks), relpath, ids[0], ids[-1])

    # ---------- busca ----------
    def search(self, query_vec: np.ndarray, k: int = 4) -> list[RetrievedChunk]:
        if self.index is None or self.index.ntotal == 0:
            return []
        q = query_vec.reshape(1, -1).astype("float32")
        scores, ids = self.index.search(q, k)
        out: list[RetrievedChunk] = []
        for score, cid in zip(scores[0].tolist(), ids[0].tolist()):
            if cid == -1:
                continue
            meta = self.manifest["chunks"].get(str(cid))
            if not meta:
                continue
            out.append(RetrievedChunk(
                chunk_id=cid, score=float(score),
                text=meta["text"], source=meta["file"], chunk_idx=meta["idx"],
            ))
        return out

    # ---------- introspecção ----------
    def file_hash(self, relpath: str) -> str | None:
        meta = self.manifest["files"].get(relpath)
        return meta.get("hash") if meta else None

    def known_files(self) -> set[str]:
        return set(self.manifest["files"].keys())

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0
