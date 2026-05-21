from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    TechnicalAnalysisHistoryResponse,
    TechnicalAnalysisInput,
    TechnicalAnalysisSavedResponse,
)
from app.services.technical_analysis_service import (
    create_technical_analysis,
    list_technical_analyses,
)
from app.services.record_source import normalize_record_source

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/technical", response_model=TechnicalAnalysisSavedResponse)
def create_technical_analysis_endpoint(
    payload: TechnicalAnalysisInput,
    x_record_source: Annotated[str | None, Header(alias="X-Record-Source")] = None,
    db: Session = Depends(get_db),
) -> TechnicalAnalysisSavedResponse:
    return create_technical_analysis(db, payload, record_source=normalize_record_source(x_record_source))


@router.get("/history", response_model=TechnicalAnalysisHistoryResponse)
def list_technical_analysis_history_endpoint(
    include_system: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> TechnicalAnalysisHistoryResponse:
    return list_technical_analyses(db, include_system=include_system)
