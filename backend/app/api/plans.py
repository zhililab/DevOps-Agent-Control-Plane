from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DailyContextInput, DailyPlanHistoryResponse, DailyPlanSavedResponse
from app.services.plan_service import create_daily_plan, list_daily_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/daily", response_model=DailyPlanSavedResponse)
def create_daily_plan_endpoint(
    payload: DailyContextInput,
    db: Session = Depends(get_db),
) -> DailyPlanSavedResponse:
    return create_daily_plan(db, payload)


@router.get("/history", response_model=DailyPlanHistoryResponse)
def list_daily_plans_endpoint(db: Session = Depends(get_db)) -> DailyPlanHistoryResponse:
    return list_daily_plans(db)
