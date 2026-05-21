from datetime import datetime

from app.models import utcnow
from app.time_utils import business_date_from_utc, format_utc_datetime


def test_utcnow_returns_naive_datetime_for_db_compatibility() -> None:
    value = utcnow()
    assert value.tzinfo is None


def test_business_date_uses_shanghai_timezone() -> None:
    assert business_date_from_utc(datetime(2026, 5, 21, 16, 45, 36)).isoformat() == "2026-05-22"


def test_public_datetime_format_marks_utc() -> None:
    assert format_utc_datetime(datetime(2026, 5, 21, 16, 45, 36)) == "2026-05-21T16:45:36.000000Z"
