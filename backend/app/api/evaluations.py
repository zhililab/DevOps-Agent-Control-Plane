from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    DecisionFeedbackCreate,
    DecisionFeedbackRead,
    DecisionFeedbackSummaryResponse,
    EvaluationCaseListResponse,
    EvaluationRunRead,
    EvaluationRunRequest,
    LlmInvocationListResponse,
    LlmProviderStatusResponse,
    PilotComparisonResponse,
    PilotMeasurementCreate,
    PilotMeasurementRead,
)
from app.services.evaluation_service import (
    create_decision_feedback,
    create_pilot_measurement,
    get_feedback_summary,
    get_latest_evaluation_run,
    get_pilot_comparison,
    list_evaluation_cases,
    list_llm_invocations,
    run_evaluation,
)
from app.services.evaluation_access import require_evaluation_write_access
from app.services.llm_provider import provider_status


router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/provider-status", response_model=LlmProviderStatusResponse)
def get_provider_status_endpoint() -> LlmProviderStatusResponse:
    return LlmProviderStatusResponse.model_validate(provider_status(get_settings()))


@router.get("/cases", response_model=EvaluationCaseListResponse)
def list_evaluation_cases_endpoint() -> EvaluationCaseListResponse:
    return list_evaluation_cases()


@router.post("/runs", response_model=EvaluationRunRead)
def run_evaluation_endpoint(
    payload: EvaluationRunRequest,
    _: None = Depends(require_evaluation_write_access),
    db: Session = Depends(get_db),
) -> EvaluationRunRead:
    return run_evaluation(db, payload)


@router.get("/runs/latest", response_model=EvaluationRunRead | None)
def get_latest_evaluation_run_endpoint(db: Session = Depends(get_db)) -> EvaluationRunRead | None:
    return get_latest_evaluation_run(db)


@router.get("/invocations", response_model=LlmInvocationListResponse)
def list_llm_invocations_endpoint(
    orchestration_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> LlmInvocationListResponse:
    return list_llm_invocations(db, orchestration_id=orchestration_id, limit=limit)


@router.post("/feedback", response_model=DecisionFeedbackRead)
def create_decision_feedback_endpoint(
    payload: DecisionFeedbackCreate,
    _: None = Depends(require_evaluation_write_access),
    db: Session = Depends(get_db),
) -> DecisionFeedbackRead:
    return create_decision_feedback(db, payload)


@router.get("/feedback-summary", response_model=DecisionFeedbackSummaryResponse)
def get_feedback_summary_endpoint(db: Session = Depends(get_db)) -> DecisionFeedbackSummaryResponse:
    return get_feedback_summary(db)


@router.post("/pilot-measurements", response_model=PilotMeasurementRead)
def create_pilot_measurement_endpoint(
    payload: PilotMeasurementCreate,
    _: None = Depends(require_evaluation_write_access),
    db: Session = Depends(get_db),
) -> PilotMeasurementRead:
    return create_pilot_measurement(db, payload)


@router.get("/pilot-comparison", response_model=PilotComparisonResponse)
def get_pilot_comparison_endpoint(
    subject: str | None = Query(default=None, max_length=120),
    team_subject: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
) -> PilotComparisonResponse:
    return get_pilot_comparison(db, subject=subject, team_subject=team_subject)
