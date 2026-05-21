from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def as_utc_naive(value: datetime | None) -> datetime:
    if value is None:
        return utcnow_naive()
    return as_utc_aware(value).replace(tzinfo=None)


def format_utc_datetime(value: datetime) -> str:
    return as_utc_aware(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def get_business_timezone_name() -> str:
    return get_settings().business_timezone


def get_business_timezone() -> ZoneInfo:
    timezone_name = get_business_timezone_name()
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def business_date_from_utc(value: datetime | None = None) -> date:
    return as_utc_aware(as_utc_naive(value)).astimezone(get_business_timezone()).date()
