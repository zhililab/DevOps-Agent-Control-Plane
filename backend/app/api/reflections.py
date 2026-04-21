from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DailyReflectionHistoryResponse,
    DailyReflectionInput,
    DailyReflectionSavedResponse,
    ReflectionEntryCreate,
    ReflectionEntryRead,
    ReflectionEntryUpdate,
)
from app.services.reflection_service import (
    create_daily_reflection,
    create_reflection,
    list_daily_reflections,
    list_reflections,
    update_reflection,
)

router = APIRouter(prefix="/reflections", tags=["reflections"])


@router.post("", response_model=ReflectionEntryRead)
def create_reflection_endpoint(
    payload: ReflectionEntryCreate, db: Session = Depends(get_db)
) -> ReflectionEntryRead:
    return create_reflection(db, payload)


@router.post("/daily", response_model=DailyReflectionSavedResponse)
def create_daily_reflection_endpoint(
    payload: DailyReflectionInput,
    db: Session = Depends(get_db),
) -> DailyReflectionSavedResponse:
    return create_daily_reflection(db, payload)


@router.get("", response_model=list[ReflectionEntryRead])
def list_reflections_endpoint(db: Session = Depends(get_db)) -> list[ReflectionEntryRead]:
    return list_reflections(db)


@router.get("/history", response_model=DailyReflectionHistoryResponse)
def list_daily_reflections_endpoint(
    db: Session = Depends(get_db),
) -> DailyReflectionHistoryResponse:
    return list_daily_reflections(db)


@router.put("/{reflection_id}", response_model=ReflectionEntryRead)
def update_reflection_endpoint(
    reflection_id: int,
    payload: ReflectionEntryUpdate,
    db: Session = Depends(get_db),
) -> ReflectionEntryRead:
    reflection = update_reflection(db, reflection_id, payload)
    if reflection is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return reflection
