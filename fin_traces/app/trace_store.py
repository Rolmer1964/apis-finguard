"""Trace store em memória (deque sem limite) + persistência opcional em disco.

Portado do trace store de `finguard8/app/src/graph.py` (`_traces`,
`_store_trace`, `get_traces`, `clear_traces`, `inject_trace`, `sum_timings`).
Diferenças:
- não há `_store_trace` que *monta* a entrada a partir do resultado do grafo:
  aqui a entrada já chega pronta no corpo do `POST /v1/traces` (o
  `fin_orchestrator` a monta). `append_trace` só normaliza os campos derivados
  (`timestamp`, `total_ms`) se vierem ausentes;
- opção `TRACES_PERSIST_PATH`: o deque é despejado em JSON a cada escrita e
  recarregado no startup.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from pathlib import Path

from .timeutil import now_brt

logger = logging.getLogger("fin_traces.store")

_traces: deque[dict] = deque()
_lock = threading.Lock()
_persist_path: Path | None = None


def sum_timings(tm: dict) -> int:
    tm = tm or {}
    return (
        (tm.get("guardrail_input") or 0)
        + (tm.get("triage") or 0)
        + (tm.get("risk") or 0)
        + (tm.get("report") or 0)
        + (tm.get("guardrail_output") or 0)
    )


# ── persistência ─────────────────────────────────────────────────────────────

def configure_persistence(path: str | None) -> None:
    """Chamado no startup. Define o arquivo de dump e recarrega o que houver."""
    global _persist_path
    if not path:
        _persist_path = None
        return
    _persist_path = Path(path)
    if _persist_path.exists():
        try:
            data = json.loads(_persist_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                with _lock:
                    _traces.clear()
                    _traces.extend(data)  # arquivo guarda a ordem do deque (mais recente primeiro)
                logger.info("traces: %d entrada(s) recarregada(s) de %s", len(data), _persist_path)
        except Exception:
            logger.exception("traces: falha ao recarregar %s", _persist_path)


def _dump_locked() -> None:
    if _persist_path is None:
        return
    try:
        _persist_path.parent.mkdir(parents=True, exist_ok=True)
        _persist_path.write_text(json.dumps(list(_traces), ensure_ascii=False), encoding="utf-8")
    except Exception:
        logger.exception("traces: falha ao persistir em %s", _persist_path)


# ── operações ────────────────────────────────────────────────────────────────

def append_trace(entry: dict) -> int:
    """Insere uma entrada nova no topo do log. Devolve o total após a inserção."""
    e = dict(entry)
    if not e.get("timestamp"):
        e["timestamp"] = now_brt().strftime("%H:%M:%S")
    if e.get("total_ms") in (None, 0):
        e["total_ms"] = sum_timings(e.get("timings_ms") or {})
    with _lock:
        _traces.appendleft(e)
        _dump_locked()
        return len(_traces)


def inject_trace(entry: dict) -> None:
    """Insere entrada diretamente (usado na recomposição a partir de relatório)."""
    with _lock:
        _traces.appendleft(dict(entry))
        _dump_locked()


def get_traces() -> list[dict]:
    with _lock:
        return list(_traces)


def clear_traces() -> int:
    with _lock:
        n = len(_traces)
        _traces.clear()
        _dump_locked()
    return n
