from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import MonetizationEvent, SubscriptionProfile, UsageCounter
from app.schemas import MonetizationEventRead, SubscriptionProfileRead, UsageCounterRead


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


def _safe_json_dict(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
