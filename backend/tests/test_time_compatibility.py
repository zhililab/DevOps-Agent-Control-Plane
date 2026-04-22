from app.models import utcnow


def test_utcnow_returns_naive_datetime_for_db_compatibility() -> None:
    value = utcnow()
    assert value.tzinfo is None
