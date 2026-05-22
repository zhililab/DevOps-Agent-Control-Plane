from __future__ import annotations

import json
from calendar import monthrange
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import (
    MonetizationEvent,
    MonetizationEventKind,
    SubscriptionProfile,
    SubscriptionStatus,
    SubscriptionTier,
    UsageCounter,
    UsageMetric,
)
from app.schemas import (
    MonetizationEventRead,
    MonetizationTier,
    SubscriptionLifecycleResponse,
    SubscriptionProfileRead,
    UsageCounterRead,
)
from app.time_utils import business_date_from_utc, utcnow_naive


TIER_ENTITLEMENTS: dict[str, dict[str, object]] = {
    "free": {
        "workflow_runs": 25,
        "queued_runs": 25,
        "max_enabled_steps": 1,
        "policy_templates": False,
        "approval_gates": False,
    },
    "pro": {
        "workflow_runs": 300,
        "queued_runs": 300,
        "max_enabled_steps": 3,
        "policy_templates": True,
        "approval_gates": False,
    },
    "power": {
        "workflow_runs": 2000,
        "queued_runs": 2000,
        "max_enabled_steps": 3,
        "policy_templates": True,
        "approval_gates": True,
    },
}


def get_subscription_profile(db: Session, *, subject: str) -> SubscriptionProfileRead | None:
    profile = (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )
    if profile is None:
        return None
    return _to_subscription_profile_read(profile)


def list_usage_counters(db: Session, *, subject: str) -> list[UsageCounterRead]:
    profile = (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )
    if profile is None:
        return []

    counters = (
        db.query(UsageCounter)
        .filter(UsageCounter.subscription_profile_id == profile.id)
        .order_by(
            UsageCounter.metric.asc(),
            UsageCounter.period_start.desc(),
            UsageCounter.period_end.desc(),
            UsageCounter.id.desc(),
        )
        .all()
    )
    return [UsageCounterRead.model_validate(counter) for counter in counters]


def list_monetization_events(db: Session, *, limit: int) -> list[MonetizationEventRead]:
    events = (
        db.query(MonetizationEvent)
        .order_by(MonetizationEvent.created_at.desc(), MonetizationEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [_to_monetization_event_read(event) for event in events]


def start_manual_checkout(
    db: Session,
    *,
    subject: str,
    target_tier: MonetizationTier,
    billing_provider: str = "manual",
) -> SubscriptionLifecycleResponse:
    now = utcnow_naive()
    profile = _get_latest_profile_model(db, subject=subject)
    previous_tier = profile.tier.value if profile is not None else None
    action = "checkout_completed" if profile is None else "tier_changed"

    if profile is None:
        profile = SubscriptionProfile(
            subject=subject,
            tier=SubscriptionTier(target_tier),
            status=SubscriptionStatus.active,
            billing_provider=billing_provider,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.flush()
    else:
        profile.tier = SubscriptionTier(target_tier)
        profile.status = SubscriptionStatus.active
        profile.billing_provider = billing_provider
        profile.cancel_at_period_end = False
        profile.current_period_start = profile.current_period_start or now
        profile.current_period_end = profile.current_period_end or (now + timedelta(days=30))
        profile.updated_at = now

    entitlements = _entitlements_for_tier(target_tier)
    profile.entitlements_json = json.dumps(entitlements, sort_keys=True, separators=(",", ":"))
    counters = _upsert_current_period_counters(db, profile=profile, entitlements=entitlements, now=now)
    event = _append_subscription_event(
        db,
        profile=profile,
        action=action,
        now=now,
        payload={
            "action": action,
            "provider": billing_provider,
            "subject": subject,
            "previous_tier": previous_tier,
            "new_tier": target_tier,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def cancel_subscription(db: Session, *, subject: str) -> SubscriptionLifecycleResponse:
    profile = _get_latest_profile_model(db, subject=subject)
    now = utcnow_naive()
    if profile is None:
        profile = SubscriptionProfile(
            subject=subject,
            tier=SubscriptionTier.free,
            status=SubscriptionStatus.inactive,
            billing_provider="manual",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=True,
            entitlements_json=json.dumps(_entitlements_for_tier("free"), sort_keys=True, separators=(",", ":")),
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.flush()
    else:
        profile.cancel_at_period_end = True
        profile.updated_at = now

    counters = _upsert_current_period_counters(
        db,
        profile=profile,
        entitlements=_safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value),
        now=now,
    )
    event = _append_subscription_event(
        db,
        profile=profile,
        action="cancel_requested",
        now=now,
        payload={
            "action": "cancel_requested",
            "provider": profile.billing_provider,
            "subject": subject,
            "tier": profile.tier.value,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def reactivate_subscription(db: Session, *, subject: str) -> SubscriptionLifecycleResponse:
    profile = _get_latest_profile_model(db, subject=subject)
    now = utcnow_naive()
    if profile is None:
        return start_manual_checkout(db, subject=subject, target_tier="free", billing_provider="manual")

    profile.cancel_at_period_end = False
    if profile.status == SubscriptionStatus.canceled:
        profile.status = SubscriptionStatus.active
    profile.updated_at = now
    counters = _upsert_current_period_counters(
        db,
        profile=profile,
        entitlements=_safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value),
        now=now,
    )
    event = _append_subscription_event(
        db,
        profile=profile,
        action="reactivated",
        now=now,
        payload={
            "action": "reactivated",
            "provider": profile.billing_provider,
            "subject": subject,
            "tier": profile.tier.value,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def _to_subscription_profile_read(profile: SubscriptionProfile) -> SubscriptionProfileRead:
    return SubscriptionProfileRead(
        id=profile.id,
        subject=profile.subject,
        tier=profile.tier,
        status=profile.status,
        billing_provider=profile.billing_provider,
        external_customer_id=profile.external_customer_id,
        external_subscription_id=profile.external_subscription_id,
        current_period_start=profile.current_period_start,
        current_period_end=profile.current_period_end,
        cancel_at_period_end=profile.cancel_at_period_end,
        entitlements=_safe_json_dict(profile.entitlements_json),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _to_monetization_event_read(event: MonetizationEvent) -> MonetizationEventRead:
    return MonetizationEventRead(
        id=event.id,
        subscription_profile_id=event.subscription_profile_id,
        usage_counter_id=event.usage_counter_id,
        event_kind=event.event_kind,
        event=_safe_json_dict(event.event_json),
        created_at=event.created_at,
    )


def _get_latest_profile_model(db: Session, *, subject: str) -> SubscriptionProfile | None:
    return (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )


def _entitlements_for_tier(tier: str) -> dict[str, object]:
    return dict(TIER_ENTITLEMENTS[tier])


def _current_month_bounds(now) -> tuple:
    business_day = business_date_from_utc(now)
    period_start = business_day.replace(day=1)
    period_end = business_day.replace(day=monthrange(business_day.year, business_day.month)[1])
    return period_start, period_end


def _upsert_current_period_counters(
    db: Session,
    *,
    profile: SubscriptionProfile,
    entitlements: dict[str, object],
    now,
) -> list[UsageCounter]:
    period_start, period_end = _current_month_bounds(now)
    counters: list[UsageCounter] = []
    for metric in (UsageMetric.workflow_runs, UsageMetric.queued_runs):
        counter = (
            db.query(UsageCounter)
            .filter(
                UsageCounter.subscription_profile_id == profile.id,
                UsageCounter.metric == metric,
                UsageCounter.period_start == period_start,
                UsageCounter.period_end == period_end,
            )
            .order_by(UsageCounter.id.desc())
            .first()
        )
        if counter is None:
            counter = UsageCounter(
                subscription_profile_id=profile.id,
                metric=metric,
                period_start=period_start,
                period_end=period_end,
                used=0,
                limit=int(entitlements.get(metric.value, 0) or 0),
                created_at=now,
                updated_at=now,
            )
            db.add(counter)
        else:
            counter.limit = int(entitlements.get(metric.value, counter.limit) or counter.limit)
            counter.updated_at = now
        counters.append(counter)
    db.flush()
    return counters


def _append_subscription_event(
    db: Session,
    *,
    profile: SubscriptionProfile,
    action: str,
    now,
    payload: dict[str, object],
) -> MonetizationEvent:
    event = MonetizationEvent(
        subscription_profile_id=profile.id,
        usage_counter_id=None,
        event_kind=MonetizationEventKind.subscription_changed,
        event_json=json.dumps({"version": 1, **payload}, sort_keys=True, separators=(",", ":")),
        created_at=now,
    )
    db.add(event)
    db.flush()
    return event


def _safe_json_dict(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
