from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DailyContextInput, DailyPlanHistoryResponse, DailyPlanSavedResponse
from app.services.plan_service import create_daily_plan, list_daily_plans
from app.services.record_source import normalize_record_source

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/daily", response_model=DailyPlanSavedResponse)
def create_daily_plan_endpoint(
    payload: DailyContextInput,
    x_record_source: Annotated[str | None, Header(alias="X-Record-Source")] = None,
    db: Session = Depends(get_db),
) -> DailyPlanSavedResponse:
    return create_daily_plan(db, payload, record_source=normalize_record_source(x_record_source))


@router.get("/history", response_model=DailyPlanHistoryResponse)
def list_daily_plans_endpoint(
    include_system: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> DailyPlanHistoryResponse:
    return list_daily_plans(db, include_system=include_system)
