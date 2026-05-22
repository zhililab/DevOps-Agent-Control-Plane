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


def test_manual_checkout_creates_active_profile_counters_and_event(client) -> None:
    response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "commercial-user", "target_tier": "pro"},
    )

    assert response.status_code == 200
    payload = response.json()
    profile = payload["profile"]
    assert profile["subject"] == "commercial-user"
    assert profile["tier"] == "pro"
    assert profile["status"] == "active"
    assert profile["billing_provider"] == "manual"
    assert profile["cancel_at_period_end"] is False
    assert profile["entitlements"]["workflow_runs"] == 300
    assert profile["entitlements"]["queued_runs"] == 300
    counters = payload["counters"]
    assert {item["metric"] for item in counters} == {"workflow_runs", "queued_runs"}
    assert {item["limit"] for item in counters} == {300}
    assert payload["event"]["event_kind"] == "subscription_changed"
    assert payload["event"]["event"]["action"] == "checkout_completed"

    profile_response = client.get("/api/monetization/profile?subject=commercial-user")
    assert profile_response.status_code == 200
    assert profile_response.json()["profile"]["tier"] == "pro"


def test_manual_checkout_tier_change_preserves_counter_usage(client) -> None:
    create_response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "usage-preserved", "target_tier": "pro"},
    )
    assert create_response.status_code == 200
    counter_id = create_response.json()["counters"][0]["id"]

    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        counter = db.get(UsageCounter, counter_id)
        assert counter is not None
        counter.used = 17
        db.commit()
    finally:
        db_generator.close()

    upgrade_response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "usage-preserved", "target_tier": "power"},
    )

    assert upgrade_response.status_code == 200
    payload = upgrade_response.json()
    assert payload["profile"]["tier"] == "power"
    assert payload["event"]["event"]["action"] == "tier_changed"
    assert payload["event"]["event"]["previous_tier"] == "pro"
    upgraded_counter = next(item for item in payload["counters"] if item["id"] == counter_id)
    assert upgraded_counter["used"] == 17
    assert upgraded_counter["limit"] == 2000


def test_subscription_cancel_and_reactivate_write_audit_events(client) -> None:
    create_response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "cancel-user", "target_tier": "power"},
    )
    assert create_response.status_code == 200

    cancel_response = client.post("/api/monetization/cancel", json={"subject": "cancel-user"})
    assert cancel_response.status_code == 200
    assert cancel_response.json()["profile"]["cancel_at_period_end"] is True
    assert cancel_response.json()["event"]["event"]["action"] == "cancel_requested"

    reactivate_response = client.post("/api/monetization/reactivate", json={"subject": "cancel-user"})
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["profile"]["cancel_at_period_end"] is False
    assert reactivate_response.json()["event"]["event"]["action"] == "reactivated"


def test_manual_checkout_rejects_invalid_tier_and_empty_subject(client) -> None:
    invalid_tier = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "commercial-user", "target_tier": "enterprise"},
    )
    empty_subject = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "   ", "target_tier": "pro"},
    )

    assert invalid_tier.status_code == 422
    assert empty_subject.status_code == 422
