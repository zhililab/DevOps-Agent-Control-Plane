from fastapi import APIRouter, Depends
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

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/technical", response_model=TechnicalAnalysisSavedResponse)
def create_technical_analysis_endpoint(
    payload: TechnicalAnalysisInput,
    db: Session = Depends(get_db),
) -> TechnicalAnalysisSavedResponse:
    return create_technical_analysis(db, payload)


@router.get("/history", response_model=TechnicalAnalysisHistoryResponse)
def list_technical_analysis_history_endpoint(
    db: Session = Depends(get_db),
) -> TechnicalAnalysisHistoryResponse:
    return list_technical_analyses(db)
