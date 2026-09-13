"""Fuso BRT (UTC-3) e relógio. Portado de `finguard8/app/src/settings.py`."""

from datetime import datetime, timedelta, timezone

TZ_BRT = timezone(timedelta(hours=-3))


def now_brt() -> datetime:
    return datetime.now(TZ_BRT)
