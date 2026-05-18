from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import MonetizationEventRead, SubscriptionProfileRead, UsageCounterRead
from app.services.monetization_service import (
    get_subscription_profile,
    list_monetization_events,
    list_usage_counters,
)

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
    db: Session = Depends(get_db),
) -> dict[str, list[MonetizationEventRead]]:
    return {"events": list_monetization_events(db, limit=limit)}
