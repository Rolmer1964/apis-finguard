"""Fuso horário de Brasília (UTC-3) e relógio da aplicação."""

from datetime import datetime, timedelta, timezone

TZ_BRT = timezone(timedelta(hours=-3))


def now_brt() -> datetime:
    return datetime.now(TZ_BRT)
