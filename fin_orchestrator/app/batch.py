"""Processamento de CSV em lote com controle adaptativo (AIMD).

Portado de `finguard8/app/src/main.py` (`_analyze_with_retry` + `_run_batch`).
Diferenças:
- cada registro chama `pipeline.analyze_one` (HTTP) em vez do grafo local;
- "throttling" é detectado por `DownstreamError.is_throttling` (código
  `BEDROCK_THROTTLING` de qualquer folha de Bedrock);
- não há arquivo `failed_*.json` em disco — os pendentes ficam só em memória
  entre passes; ao final, o relatório é gerado pelo `fin_report_writer`.
"""

from __future__ import annotations

import concurrent.futures
import csv
import io
import logging
import time

from . import clients
from .config import get_settings
from .pipeline import analyze_one, blocked_record
from .profanity import mask as mask_profanity
from .timeutil import now_brt

logger = logging.getLogger("fin_orchestrator.batch")


def parse_csv(raw: str) -> list[dict]:
    """Extrai as linhas úteis do CSV. Exige a coluna `texto_reclamacao`."""
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "texto_reclamacao" not in reader.fieldnames:
        raise ValueError("CSV precisa ter ao menos a coluna 'texto_reclamacao'")
    rows: list[dict] = []
    for i, row in enumerate(reader, start=1):
        texto = (row.get("texto_reclamacao") or "").strip()
        if not texto:
            continue
        rows.append({
            "texto": texto,
            "produto_hint": (row.get("produto") or "").strip() or None,
            "canal": (row.get("canal") or "").strip() or "Não informado",
            "rec_id": (row.get("id") or f"REC-{i:05d}"),
        })
    return rows


def _analyze_with_retry(row: dict, rate_limit_delay: float, max_retries: int) -> dict:
    if rate_limit_delay > 0:
        time.sleep(rate_limit_delay)
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return analyze_one(
                row["texto"], row["produto_hint"], canal=row["canal"], record_id=row["rec_id"],
            )
        except clients.DownstreamError as exc:
            last_exc = exc
            if exc.is_throttling:
                raise  # throttling não faz retry local — vai para o próximo passe
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("[%s] tentativa %d/%d falhou — retry em %ds: %s",
                               row["rec_id"], attempt + 1, max_retries + 1, wait, exc)
                time.sleep(wait)
    logger.error("[%s] todas as tentativas falharam: %s", row["rec_id"], last_exc)
    raise last_exc  # type: ignore[misc]


def _error_record(rec_id: str, canal: str, texto: str, msg: str) -> dict:
    return {
        "id": rec_id, "canal": canal, "texto_original": mask_profanity(texto),
        "category": "Erro", "product": "—", "sentiment": "—", "urgency": "—",
        "summary": msg, "risk_level": "—", "risk_justification": "",
    }


def _make_processor(delay: float, retries: int):
    def process_row(row: dict) -> dict:
        rec_id, texto, canal = row["rec_id"], row["texto"], row["canal"]
        try:
            r = _analyze_with_retry(row, delay, retries)
        except clients.DownstreamError as exc:
            if exc.is_throttling:
                logger.warning("[%s] throttling — agendado para o próximo passe", rec_id)
                return {"_throttled": True, "_row": row}
            logger.error("[%s] falha definitiva: %s", rec_id, exc)
            return _error_record(rec_id, canal, texto, f"[falha: {exc}]")
        if r.get("blocked"):
            return blocked_record(rec_id, canal, r)
        return {"id": rec_id, "canal": canal, **r}

    return process_row


def run_batch(rows: list[dict], label: str | None, filename: str | None) -> dict:
    """Roda o CSV em passes AIMD e gera o relatório no `fin_report_writer`."""
    s = get_settings()
    t_start = time.time()
    started_at = now_brt().strftime("%Y-%m-%d %H:%M:%S (UTC-3)")

    workers = s.BATCH_MAX_WORKERS
    delay = s.BATCH_RATE_LIMIT_DELAY
    retries = s.BATCH_MAX_RETRIES
    max_passes = s.BATCH_MAX_PASSES

    pending = rows
    all_results: list[dict] = []
    pass_stats: list[dict] = []

    for pass_num in range(max_passes):
        if not pending:
            break
        if pass_num > 0:
            prev_rate = pass_stats[-1]["throttle_rate"]
            wait = s.BATCH_RETRY_DELAY * (1.0 + prev_rate)
            logger.info("batch passe %d/%d: aguardando %.0fs (throttle anterior=%.0f%%)",
                        pass_num + 1, max_passes, wait, prev_rate * 100)
            time.sleep(wait)

        logger.info("batch passe %d/%d: %d registros | workers=%d delay=%.2fs retries=%d",
                    pass_num + 1, max_passes, len(pending), workers, delay, retries)

        pass_start = time.time()
        next_pending: list[dict] = []
        success = 0
        fn = _make_processor(delay, retries)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(fn, pending):
                if res.get("_throttled"):
                    next_pending.append(res["_row"])
                else:
                    all_results.append(res)
                    success += 1

        pass_elapsed = time.time() - pass_start
        throttled = len(next_pending)
        total_pass = len(pending)
        throttle_rate = throttled / total_pass if total_pass else 0.0
        pass_stats.append({
            "pass_num": pass_num + 1, "workers": workers, "delay_s": round(delay, 2),
            "retries": retries, "total": total_pass, "success": success,
            "throttled": throttled, "throttle_rate": round(throttle_rate, 4),
            "throttle_pct": round(throttle_rate * 100, 1), "duration_s": round(pass_elapsed, 1),
            "throughput_rpm": round(success / pass_elapsed * 60, 1) if pass_elapsed > 0 else 0.0,
        })
        logger.info("batch passe %d/%d: sucesso=%d throttled=%d (%.0f%%) | %.1fs",
                    pass_num + 1, max_passes, success, throttled, throttle_rate * 100, pass_elapsed)

        if throttle_rate > 0.05:
            workers = max(1, workers // 2)
            delay = round(delay + 1.0, 2)
            logger.info("AIMD ↓ throttle=%.0f%% → workers=%d delay=%.2fs", throttle_rate * 100, workers, delay)
        elif throttled == 0:
            workers = min(s.BATCH_MAX_WORKERS, workers + 1)
            delay = round(max(0.0, delay - 0.5), 2)
            logger.info("AIMD ↑ throttle=0%% → workers=%d delay=%.2fs", workers, delay)

        retries = max(0, retries - 1)
        pending = next_pending

    for row in pending:
        logger.error("[%s] esgotou %d passes — throttling persistente", row["rec_id"], max_passes)
        all_results.append(_error_record(
            row["rec_id"], row["canal"], row["texto"],
            f"[falha após {max_passes} passes — throttling persistente]",
        ))

    finished_at = now_brt().strftime("%Y-%m-%d %H:%M:%S (UTC-3)")
    elapsed_s = time.time() - t_start
    meta = {
        "started_at": started_at, "finished_at": finished_at, "elapsed_s": elapsed_s,
        "pass_stats": pass_stats, "label": label or None, "filename": filename,
    }
    report = clients.create_report(all_results, meta)

    ok = sum(1 for r in all_results if r.get("category") not in ("Erro", "Bloqueado"))
    return {
        "stem": report["stem"],
        "paths": report["paths"],
        "total": len(all_results),
        "ok": ok,
        "blocked": sum(1 for r in all_results if r.get("category") == "Bloqueado"),
        "errors": sum(1 for r in all_results if r.get("category") == "Erro"),
        "pass_stats": pass_stats,
        "elapsed_s": round(elapsed_s, 1),
    }
