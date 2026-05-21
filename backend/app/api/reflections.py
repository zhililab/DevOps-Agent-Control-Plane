from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
from app.services.record_source import normalize_record_source
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
    x_record_source: Annotated[str | None, Header(alias="X-Record-Source")] = None,
    db: Session = Depends(get_db),
) -> DailyReflectionSavedResponse:
    return create_daily_reflection(db, payload, record_source=normalize_record_source(x_record_source))


@router.get("", response_model=list[ReflectionEntryRead])
def list_reflections_endpoint(db: Session = Depends(get_db)) -> list[ReflectionEntryRead]:
    return list_reflections(db)


@router.get("/history", response_model=DailyReflectionHistoryResponse)
def list_daily_reflections_endpoint(
    include_system: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> DailyReflectionHistoryResponse:
    return list_daily_reflections(db, include_system=include_system)


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
