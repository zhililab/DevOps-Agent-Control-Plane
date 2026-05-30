from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    CommercialMetricsResponse,
    EntitlementBootstrapResponse,
    ManualCheckoutRequest,
    MonetizationEventRead,
    PilotCloseoutReportResponse,
    PilotReadinessReportResponse,
    SubscriptionCancelRequest,
    SubscriptionLifecycleResponse,
    SubscriptionProfileRead,
    UsageCounterRead,
)
from app.services.monetization_service import (
    cancel_subscription,
    get_commercial_metrics,
    get_pilot_closeout_report,
    get_pilot_readiness_report,
    get_subscription_profile,
    list_monetization_events,
    list_usage_counters,
    reactivate_subscription,
    start_manual_checkout,
)
from app.services.entitlement_service import sign_entitlement_token

router = APIRouter(prefix="/monetization", tags=["monetization"])


@router.get("/profile")
def get_monetization_profile(
    subject: str = Query(..., min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> dict[str, SubscriptionProfileRead | None]:
    return {"profile": get_subscription_profile(db, subject=subject)}


@router.get("/usage")
def get_monetization_usage(
    subject: str = Query(..., min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> dict[str, list[UsageCounterRead]]:
    return {"counters": list_usage_counters(db, subject=subject)}


@router.get("/events")
def get_monetization_events(
    limit: int = Query(default=50, ge=1, le=100),
    subject: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> dict[str, list[MonetizationEventRead]]:
    return {"events": list_monetization_events(db, limit=limit, subject=subject)}


@router.get("/entitlement", response_model=EntitlementBootstrapResponse)
def get_monetization_entitlement(
    subject: str = Query(..., min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> EntitlementBootstrapResponse:
    settings = get_settings()
    if not settings.entitlement_secret.strip():
        raise HTTPException(status_code=503, detail="Entitlement signing is unavailable.")

    normalized_subject = subject.strip()
    profile = get_subscription_profile(db, subject=normalized_subject)
    if profile is None:
        raise HTTPException(status_code=404, detail="No subscription profile found for this subject.")
    if profile.status != "active":
        raise HTTPException(status_code=409, detail="Subscription is not active.")
    now = datetime.now(timezone.utc)
    if profile.current_period_end and profile.current_period_end.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(status_code=409, detail="Subscription period has ended.")

    ttl_seconds = max(300, int(settings.public_entitlement_bootstrap_ttl_seconds))
    token = sign_entitlement_token(
        secret=settings.entitlement_secret,
        tier=profile.tier,
        user_id=normalized_subject,
        ttl_seconds=ttl_seconds,
    )
    return EntitlementBootstrapResponse(
        token=token,
        tier=profile.tier,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )


@router.get("/commercial-metrics", response_model=CommercialMetricsResponse)
def get_commercial_metrics_endpoint(
    days: int = Query(default=7, ge=1, le=30),
    subject: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> CommercialMetricsResponse:
    return get_commercial_metrics(db, days=days, subject=subject)


@router.get("/pilot-report", response_model=PilotReadinessReportResponse)
def get_pilot_readiness_report_endpoint(
    days: int = Query(default=7, ge=1, le=30),
    subject: str | None = Query(default=None, min_length=1, max_length=120),
    team_subject: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> PilotReadinessReportResponse:
    return get_pilot_readiness_report(
        db,
        days=days,
        subject=subject,
        team_subject=team_subject,
    )


@router.get("/pilot-closeout", response_model=PilotCloseoutReportResponse)
def get_pilot_closeout_report_endpoint(
    days: int = Query(default=7, ge=1, le=30),
    subject: str | None = Query(default=None, min_length=1, max_length=120),
    team_subject: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
) -> PilotCloseoutReportResponse:
    return get_pilot_closeout_report(
        db,
        days=days,
        subject=subject,
        team_subject=team_subject,
    )


@router.post("/checkout/manual", response_model=SubscriptionLifecycleResponse)
def post_manual_checkout(
    payload: ManualCheckoutRequest,
    db: Session = Depends(get_db),
) -> SubscriptionLifecycleResponse:
    return start_manual_checkout(
        db,
        subject=payload.subject,
        target_tier=payload.target_tier,
        billing_provider=payload.billing_provider,
    )


@router.post("/cancel", response_model=SubscriptionLifecycleResponse)
def post_subscription_cancel(
    payload: SubscriptionCancelRequest,
    db: Session = Depends(get_db),
) -> SubscriptionLifecycleResponse:
    return cancel_subscription(db, subject=payload.subject)


@router.post("/reactivate", response_model=SubscriptionLifecycleResponse)
def post_subscription_reactivate(
    payload: SubscriptionCancelRequest,
    db: Session = Depends(get_db),
) -> SubscriptionLifecycleResponse:
    return reactivate_subscription(db, subject=payload.subject)
