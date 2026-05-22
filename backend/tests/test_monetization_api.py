import json
from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.main import app
from app.models import (
    AgentRunLog,
    MonetizationEvent,
    MonetizationEventKind,
    SubscriptionProfile,
    SubscriptionStatus,
    SubscriptionTier,
    UsageCounter,
    UsageMetric,
    WorkflowOrchestration,
    WorkflowTemplate,
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
        other_profile = SubscriptionProfile(
            subject="other-events-subject",
            tier=SubscriptionTier.power,
            status=SubscriptionStatus.active,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add(other_profile)
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
        other_subject_event = MonetizationEvent(
            subscription_profile_id=other_profile.id,
            usage_counter_id=None,
            event_kind=MonetizationEventKind.subscription_changed,
            event_json=json.dumps({"version": "other-subject"}),
            created_at=now + timedelta(minutes=1),
        )
        db.add_all([same_time_second, other_subject_event])
        db.commit()

        response = client.get("/api/monetization/events?limit=2")

        assert response.status_code == 200
        events = response.json()["events"]
        assert [item["event"]["version"] for item in events] == ["other-subject", "second"]

        filtered_response = client.get("/api/monetization/events?subject=events-subject&limit=2")
        assert filtered_response.status_code == 200
        filtered_events = filtered_response.json()["events"]
        assert [item["event"]["version"] for item in filtered_events] == ["second", "first"]
        assert [item["event_kind"] for item in filtered_events] == ["usage_recorded", "entitlement_checked"]
    finally:
        db_generator.close()


def test_monetization_events_are_limited_and_sorted_by_newest_first_without_subject_filter(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = _now()
    try:
        profile = SubscriptionProfile(
            subject="events-global-subject",
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


def test_commercial_metrics_aggregates_subject_scoped_usage_policy_blocks_and_templates(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = _now()
    try:
        profile = SubscriptionProfile(
            subject="metrics-subject",
            tier=SubscriptionTier.power,
            status=SubscriptionStatus.active,
            billing_provider="manual",
            entitlements_json=json.dumps({"workflow_runs": 2000, "queued_runs": 2000}),
            created_at=now,
            updated_at=now,
        )
        other_profile = SubscriptionProfile(
            subject="other-metrics-subject",
            tier=SubscriptionTier.pro,
            status=SubscriptionStatus.active,
            billing_provider="manual",
            entitlements_json=json.dumps({"workflow_runs": 300, "queued_runs": 300}),
            created_at=now,
            updated_at=now,
        )
        template = WorkflowTemplate(
            name="Power Release Gate",
            description="Audited release gate",
            steps_json=json.dumps([{"step_name": "Approve", "agent_type": "planner", "enabled": True}]),
            tags_json=json.dumps(
                ["tier:power", "risk:high", "approval:required", "work-units:7", "tool:server-deploy"]
            ),
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        db.add_all([profile, other_profile, template])
        db.flush()
        db.add_all(
            [
                UsageCounter(
                    subscription_profile_id=profile.id,
                    metric=UsageMetric.workflow_runs,
                    period_start=date(2026, 5, 1),
                    period_end=date(2026, 5, 31),
                    used=0,
                    limit=2000,
                    created_at=now,
                    updated_at=now,
                ),
                UsageCounter(
                    subscription_profile_id=profile.id,
                    metric=UsageMetric.queued_runs,
                    period_start=date(2026, 5, 1),
                    period_end=date(2026, 5, 31),
                    used=0,
                    limit=2000,
                    created_at=now,
                    updated_at=now,
                ),
                MonetizationEvent(
                    subscription_profile_id=profile.id,
                    usage_counter_id=None,
                    event_kind=MonetizationEventKind.subscription_changed,
                    event_json=json.dumps({"action": "checkout_completed", "token": "should-not-leak"}),
                    created_at=now,
                ),
                MonetizationEvent(
                    subscription_profile_id=other_profile.id,
                    usage_counter_id=None,
                    event_kind=MonetizationEventKind.subscription_changed,
                    event_json=json.dumps({"action": "checkout_completed"}),
                    created_at=now,
                ),
            ]
        )
        db.flush()
        orchestration = WorkflowOrchestration(
            status="success",
            duration_ms=42,
            entry_source="test",
            subscription_tier="power",
            team_subject="platform-team",
            requested_by="sre",
            approval_actor="manager",
            approval_note="approved",
            request_json=json.dumps({"template_id": template.id}),
            result_json="{}",
            created_at=now,
            updated_at=now,
        )
        other_orchestration = WorkflowOrchestration(
            status="success",
            duration_ms=30,
            entry_source="test",
            subscription_tier="pro",
            request_json=json.dumps({"steps": [{"enabled": True}, {"enabled": True}]}),
            result_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add_all([orchestration, other_orchestration])
        db.flush()
        db.add_all(
            [
                AgentRunLog(
                    task_type="monetization.usage_recorded",
                    input_summary=json.dumps(
                        {
                            "endpoint": "/api/orchestrations/run",
                            "subject_id": "metrics-subject",
                            "orchestration_id": orchestration.id,
                            "token": "secret-value",
                        },
                        separators=(",", ":"),
                    ),
                    output_summary="usage recorded",
                    status="success",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.usage_recorded",
                    input_summary=json.dumps(
                        {
                            "endpoint": "/api/orchestrations/run",
                            "subject_id": "other-metrics-subject",
                            "orchestration_id": other_orchestration.id,
                        },
                        separators=(",", ":"),
                    ),
                    output_summary="usage recorded",
                    status="success",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.approval_required_blocked",
                    input_summary=json.dumps(
                        {"endpoint": "/api/orchestrations/run", "subject_id": "metrics-subject"},
                        separators=(",", ":"),
                    ),
                    output_summary="blocked",
                    status="blocked",
                    created_at=now,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/monetization/commercial-metrics?days=7&subject=metrics-subject")

        assert response.status_code == 200
        payload = response.json()
        assert payload["subject"] == "metrics-subject"
        assert payload["subscription_summary"]["tier_distribution"]["power"] == 1
        assert payload["subscription_summary"]["active_subjects"] == 1
        assert payload["usage_summary"]["workflow_runs_used"] == 1
        assert payload["usage_summary"]["workflow_runs_limit"] == 2000
        assert payload["policy_blocks"]["approval_required"] == 1
        assert payload["policy_blocks"]["total"] == 1
        assert payload["billable_work_units"]["total"] == 7
        assert payload["billable_work_units"]["audited_workflows"] == 1
        assert payload["top_templates"][0]["template_name"] == "Power Release Gate"
        assert payload["top_templates"][0]["billable_work_units"] == 7
        assert payload["commercial_events"] == [{"action": "checkout completed", "count": 1}]
        serialized = json.dumps(payload)
        assert "secret-value" not in serialized
        assert "should-not-leak" not in serialized
    finally:
        db_generator.close()


def test_commercial_metrics_global_view_counts_multiple_tiers_and_stable_template_order(client) -> None:
    first_response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "global-free", "target_tier": "free"},
    )
    second_response = client.post(
        "/api/monetization/checkout/manual",
        json={"subject": "global-pro", "target_tier": "pro"},
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get("/api/monetization/commercial-metrics?days=30")

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_days"] == 30
    assert payload["subscription_summary"]["tier_distribution"]["free"] >= 1
    assert payload["subscription_summary"]["tier_distribution"]["pro"] >= 1
    assert set(payload["usage_summary"]) == {
        "workflow_runs_used",
        "workflow_runs_limit",
        "queued_runs_used",
        "queued_runs_limit",
        "usage_subjects",
    }
    assert isinstance(payload["top_templates"], list)
    assert isinstance(payload["trend"], list)
    assert len(payload["trend"]) == 30
