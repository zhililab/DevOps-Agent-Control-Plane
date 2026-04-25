from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.orchestration_service import get_monetization_observability

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/monetization")
def get_monetization_observability_endpoint(
    days: int = Query(default=7),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if days not in {7, 30}:
        raise HTTPException(status_code=422, detail="days must be 7 or 30.")
    return get_monetization_observability(db, days=days)
