import json
from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.main import app
from app.models import (
    MonetizationEvent,
    MonetizationEventKind,
    SubscriptionProfile,
    SubscriptionStatus,
    SubscriptionTier,
    UsageCounter,
    UsageMetric,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_monetization_profile_returns_null_when_missing(client) -> None:
    response = client.get("/api/monetization/profile?subject=missing-subject")

    assert response.status_code == 200
    assert response.json() == {"profile": None}


def test_monetization_profile_reads_existing_profile_without_creating_data(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = _now()
    try:
        db.add(
            SubscriptionProfile(
                subject="subject-1",
                tier=SubscriptionTier.pro,
                status=SubscriptionStatus.active,
                billing_provider="stripe",
                external_customer_id="cus_123",
                external_subscription_id="sub_123",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                cancel_at_period_end=True,
                entitlements_json=json.dumps({"workflow_runs": 100, "priority_queue": True}),
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

        response = client.get("/api/monetization/profile?subject=subject-1")

        assert response.status_code == 200
        profile = response.json()["profile"]
        assert profile["subject"] == "subject-1"
        assert profile["tier"] == "pro"
        assert profile["status"] == "active"
        assert profile["entitlements"] == {"workflow_runs": 100, "priority_queue": True}
    finally:
        db_generator.close()


def test_monetization_usage_returns_empty_list_when_profile_missing(client) -> None:
    response = client.get("/api/monetization/usage?subject=missing-subject")

    assert response.status_code == 200
    assert response.json() == {"counters": []}


def test_monetization_usage_sorts_counters_deterministically_for_subject(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = _now()
    try:
        profile = SubscriptionProfile(
            subject="usage-subject",
            tier=SubscriptionTier.power,
            status=SubscriptionStatus.active,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        other_profile = SubscriptionProfile(
            subject="other-subject",
            tier=SubscriptionTier.free,
            status=SubscriptionStatus.inactive,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add_all([profile, other_profile])
        db.flush()
        db.add_all(
            [
                UsageCounter(
                    subscription_profile_id=profile.id,
                    metric=UsageMetric.workflow_runs,
                    period_start=date(2026, 5, 1),
                    period_end=date(2026, 5, 31),
                    used=7,
                    limit=100,
                    created_at=now,
                    updated_at=now,
                ),
                UsageCounter(
                    subscription_profile_id=profile.id,
                    metric=UsageMetric.workflow_runs,
                    period_start=date(2026, 4, 1),
                    period_end=date(2026, 4, 30),
                    used=3,
                    limit=100,
                    created_at=now,
                    updated_at=now,
                ),
                UsageCounter(
                    subscription_profile_id=profile.id,
                    metric=UsageMetric.queued_runs,
                    period_start=date(2026, 5, 1),
                    period_end=date(2026, 5, 31),
                    used=2,
                    limit=50,
                    created_at=now,
                    updated_at=now,
                ),
                UsageCounter(
                    subscription_profile_id=other_profile.id,
                    metric=UsageMetric.workflow_runs,
                    period_start=date(2026, 5, 1),
                    period_end=date(2026, 5, 31),
                    used=99,
                    limit=100,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/monetization/usage?subject=usage-subject")

        assert response.status_code == 200
        counters = response.json()["counters"]
        assert [(item["metric"], item["period_start"], item["used"]) for item in counters] == [
            ("queued_runs", "2026-05-01", 2),
            ("workflow_runs", "2026-05-01", 7),
            ("workflow_runs", "2026-04-01", 3),
        ]
    finally:
        db_generator.close()


def test_monetization_events_are_limited_and_sorted_by_newest_first(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = _now()
    try:
        profile = SubscriptionProfile(
            subject="events-subject",
            tier=SubscriptionTier.pro,
            status=SubscriptionStatus.active,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.flush()
        older = MonetizationEvent(
            subscription_profile_id=profile.id,
            usage_counter_id=None,
            event_kind=MonetizationEventKind.subscription_changed,
            event_json=json.dumps({"version": "older"}),
            created_at=now - timedelta(minutes=5),
        )
        same_time_first = MonetizationEvent(
            subscription_profile_id=profile.id,
            usage_counter_id=None,
            event_kind=MonetizationEventKind.entitlement_checked,
            event_json=json.dumps({"version": "first"}),
            created_at=now,
        )
        db.add_all([older, same_time_first])
        db.flush()
        same_time_second = MonetizationEvent(
            subscription_profile_id=profile.id,
            usage_counter_id=None,
            event_kind=MonetizationEventKind.usage_recorded,
            event_json=json.dumps({"version": "second"}),
            created_at=now,
        )
        db.add(same_time_second)
        db.commit()

        response = client.get("/api/monetization/events?limit=2")

        assert response.status_code == 200
        events = response.json()["events"]
        assert [item["event"]["version"] for item in events] == ["second", "first"]
        assert [item["event_kind"] for item in events] == ["usage_recorded", "entitlement_checked"]
    finally:
        db_generator.close()


def test_monetization_events_rejects_out_of_range_limit(client) -> None:
    response = client.get("/api/monetization/events?limit=101")

    assert response.status_code == 422
