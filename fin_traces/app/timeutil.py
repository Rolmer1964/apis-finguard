"""Fuso horário de Brasília (UTC-3) e relógio da aplicação.

Portado do trecho de `finguard8/app/src/settings.py` (`TZ_BRT`, `now_brt`).
"""

from datetime import datetime, timedelta, timezone

TZ_BRT = timezone(timedelta(hours=-3))


def now_brt() -> datetime:
    return datetime.now(TZ_BRT)
