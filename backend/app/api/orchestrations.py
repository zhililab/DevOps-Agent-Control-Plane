from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    WorkflowOrchestrationHistoryResponse,
    WorkflowOrchestrationMetricsResponse,
    WorkflowOrchestrationRead,
    WorkflowOrchestrationRunRequest,
    WorkflowTemplateCreate,
    WorkflowTemplateImportRequest,
    WorkflowTemplateImportResponse,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from app.services.orchestration_service import (
    create_workflow_template,
    export_workflow_templates,
    get_orchestration,
    get_orchestration_metrics,
    import_workflow_templates,
    list_orchestrations,
    list_workflow_templates,
    run_orchestration,
    update_workflow_template,
)

router = APIRouter(prefix="/orchestrations", tags=["orchestrations"])


@router.post("/run", response_model=WorkflowOrchestrationRead)
def run_orchestration_endpoint(
    payload: WorkflowOrchestrationRunRequest,
    db: Session = Depends(get_db),
    subscription_tier: Annotated[str | None, Header(alias="X-Subscription-Tier")] = None,
) -> WorkflowOrchestrationRead:
    settings = get_settings()
    tier = subscription_tier or settings.default_subscription_tier
    return run_orchestration(db, payload, subscription_tier=tier)


@router.get("/history", response_model=WorkflowOrchestrationHistoryResponse)
def list_orchestrations_endpoint(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    subscription_tier: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> WorkflowOrchestrationHistoryResponse:
    return list_orchestrations(db, status=status, subscription_tier=subscription_tier, limit=limit)


@router.get("/metrics", response_model=WorkflowOrchestrationMetricsResponse)
def get_orchestration_metrics_endpoint(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> WorkflowOrchestrationMetricsResponse:
    return get_orchestration_metrics(db, days=days)


@router.post("/templates", response_model=WorkflowTemplateRead)
def create_workflow_template_endpoint(
    payload: WorkflowTemplateCreate,
    db: Session = Depends(get_db),
) -> WorkflowTemplateRead:
    return create_workflow_template(db, payload)


@router.put("/templates/{template_id}", response_model=WorkflowTemplateRead)
def update_workflow_template_endpoint(
    template_id: int,
    payload: WorkflowTemplateUpdate,
    db: Session = Depends(get_db),
) -> WorkflowTemplateRead:
    return update_workflow_template(db, template_id, payload)


@router.get("/templates", response_model=list[WorkflowTemplateRead])
def list_workflow_templates_endpoint(
    db: Session = Depends(get_db),
    enabled: bool | None = Query(default=None),
) -> list[WorkflowTemplateRead]:
    return list_workflow_templates(db, enabled=enabled)


@router.get("/templates/export", response_model=list[WorkflowTemplateRead])
def export_workflow_templates_endpoint(
    db: Session = Depends(get_db),
) -> list[WorkflowTemplateRead]:
    return export_workflow_templates(db)


@router.post("/templates/import", response_model=WorkflowTemplateImportResponse)
def import_workflow_templates_endpoint(
    payload: WorkflowTemplateImportRequest,
    db: Session = Depends(get_db),
) -> WorkflowTemplateImportResponse:
    return import_workflow_templates(db, payload)


@router.get("/{orchestration_id}", response_model=WorkflowOrchestrationRead)
def get_orchestration_endpoint(
    orchestration_id: int,
    db: Session = Depends(get_db),
) -> WorkflowOrchestrationRead:
    return get_orchestration(db, orchestration_id)
