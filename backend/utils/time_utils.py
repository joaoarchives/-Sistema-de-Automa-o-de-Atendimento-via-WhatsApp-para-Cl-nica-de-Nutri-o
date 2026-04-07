from __future__ import annotations

import os
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

APP_TIMEZONE_NAME = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

try:
    APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)
except Exception:
    APP_TIMEZONE = UTC


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    return utc_now().replace(tzinfo=None)


def utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def db_utc_to_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC)
    return value.replace(tzinfo=UTC)


def local_today() -> date:
    return datetime.now(APP_TIMEZONE).date()


def local_now() -> datetime:
    return datetime.now(APP_TIMEZONE)


def local_schedule_to_utc(data_ref: date, horario_ref) -> datetime:
    if hasattr(horario_ref, "hour"):
        horario = time(horario_ref.hour, horario_ref.minute, getattr(horario_ref, "second", 0))
    else:
        partes = str(horario_ref).split(":")
        horas = int(partes[0])
        minutos = int(partes[1]) if len(partes) > 1 else 0
        segundos = int(partes[2]) if len(partes) > 2 else 0
        horario = time(horas, minutos, segundos)

    return datetime.combine(data_ref, horario, APP_TIMEZONE).astimezone(UTC)
