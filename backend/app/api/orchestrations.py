from typing import Annotated

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    EntitlementBootstrapResponse,
    HistoryIntegrityResponse,
    PilotScenarioListResponse,
    WorkflowCheckpointHistoryResponse,
    WorkflowEvidenceExportResponse,
    WorkflowOrchestrationHistoryResponse,
    WorkflowOrchestrationMetricsResponse,
    WorkflowOrchestrationRead,
    WorkflowOrchestrationRunRequest,
    WorkflowQueueHistoryResponse,
    WorkflowQueueJobRead,
    WorkflowQueueRunResponse,
    WorkflowTemplateCreate,
    WorkflowTemplateImportRequest,
    WorkflowTemplateImportResponse,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from app.services.history_ledger import verify_orchestration_history
from app.services.entitlement_service import (
    normalize_tier,
    resolve_entitlement_context,
    resolve_legacy_entitlement_context,
    sign_entitlement_token,
)
from app.services.orchestration_queue_service import (
    cancel_queue_job,
    enqueue_orchestration_run,
    get_queue_job,
    list_queue_jobs,
    retry_queue_job,
)
from app.services.orchestration_service import (
    create_workflow_template,
    enforce_monetization_policy_for_run,
    export_workflow_templates,
    get_orchestration,
    get_orchestration_checkpoints,
    get_orchestration_evidence_export,
    get_orchestration_metrics,
    import_builtin_workflow_templates,
    import_workflow_templates,
    list_orchestrations,
    load_builtin_workflow_templates,
    list_workflow_templates,
    run_orchestration,
    update_workflow_template,
)
from app.services.pilot_scenarios import list_pilot_scenarios

router = APIRouter(prefix="/orchestrations", tags=["orchestrations"])


@router.post("/run", response_model=WorkflowOrchestrationRead)
def run_orchestration_endpoint(
    payload: WorkflowOrchestrationRunRequest,
    db: Session = Depends(get_db),
    entitlement_token: Annotated[str | None, Header(alias="X-Entitlement")] = None,
    legacy_tier: Annotated[str | None, Header(alias="X-Subscription-Tier")] = None,
) -> WorkflowOrchestrationRead:
    settings = get_settings()
    if (
        entitlement_token is None
        and legacy_tier
        and settings.effective_allow_legacy_subscription_tier_fallback
    ):
        entitlement = resolve_legacy_entitlement_context(legacy_tier)
    else:
        entitlement = resolve_entitlement_context(
            entitlement_token,
            secret=settings.entitlement_secret,
            default_tier=settings.default_subscription_tier,
            required=settings.effective_entitlement_required,
        )
    enforce_monetization_policy_for_run(
        db,
        payload,
        tier=entitlement.tier,
        subject_id=entitlement.subject_id,
        endpoint="/api/orchestrations/run",
        billing_subject=entitlement.billing_subject,
    )
    return run_orchestration(
        db,
        payload,
        subscription_tier=entitlement.tier,
        monetization_context={
            "endpoint": "/api/orchestrations/run",
            "tier": entitlement.tier,
            "subject_id": entitlement.subject_id,
            "billing_subject": entitlement.billing_subject or "",
            "source": entitlement.source,
        },
    )


@router.get("/history", response_model=WorkflowOrchestrationHistoryResponse)
def list_orchestrations_endpoint(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    subscription_tier: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    include_steps: bool = Query(default=True),
    include_integrity: bool = Query(default=True),
    team_subject: str | None = Query(default=None),
) -> WorkflowOrchestrationHistoryResponse:
    return list_orchestrations(
        db,
        status=status,
        subscription_tier=subscription_tier,
        limit=limit,
        include_steps=include_steps,
        include_integrity=include_integrity,
        team_subject=team_subject,
    )


@router.get("/metrics", response_model=WorkflowOrchestrationMetricsResponse)
def get_orchestration_metrics_endpoint(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> WorkflowOrchestrationMetricsResponse:
    return get_orchestration_metrics(db, days=days)


@router.get("/entitlement/bootstrap", response_model=EntitlementBootstrapResponse)
def get_entitlement_bootstrap_token() -> EntitlementBootstrapResponse:
    settings = get_settings()
    if not settings.enable_public_entitlement_bootstrap:
        raise HTTPException(status_code=404, detail="Not found.")
    if not settings.entitlement_secret.strip():
        raise HTTPException(status_code=503, detail="Entitlement bootstrap is unavailable.")

    ttl_seconds = max(300, int(settings.public_entitlement_bootstrap_ttl_seconds))
    tier = normalize_tier(settings.default_subscription_tier)
    token = sign_entitlement_token(
        secret=settings.entitlement_secret,
        tier=tier,
        user_id="public-bootstrap",
        ttl_seconds=ttl_seconds,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return EntitlementBootstrapResponse(
        token=token,
        tier=tier,
        expires_at=expires_at,
    )


@router.get("/pilot-scenarios", response_model=PilotScenarioListResponse)
def list_pilot_scenarios_endpoint() -> PilotScenarioListResponse:
    return list_pilot_scenarios()


@router.post("/queue/run", response_model=WorkflowQueueRunResponse)
def enqueue_orchestration_endpoint(
    payload: WorkflowOrchestrationRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    entitlement_token: Annotated[str | None, Header(alias="X-Entitlement")] = None,
    legacy_tier: Annotated[str | None, Header(alias="X-Subscription-Tier")] = None,
) -> WorkflowQueueRunResponse:
    settings = get_settings()
    if (
        entitlement_token is None
        and legacy_tier
        and settings.effective_allow_legacy_subscription_tier_fallback
    ):
        entitlement = resolve_legacy_entitlement_context(legacy_tier)
    else:
        entitlement = resolve_entitlement_context(
            entitlement_token,
            secret=settings.entitlement_secret,
            default_tier=settings.default_subscription_tier,
            required=settings.effective_entitlement_required,
        )
    enforce_monetization_policy_for_run(
        db,
        payload,
        tier=entitlement.tier,
        subject_id=entitlement.subject_id,
        endpoint="/api/orchestrations/queue/run",
        billing_subject=entitlement.billing_subject,
    )
    return enqueue_orchestration_run(
        db,
        payload,
        subscription_tier=entitlement.tier,
        background_tasks=background_tasks,
        monetization_context={
            "endpoint": "/api/orchestrations/queue/run",
            "tier": entitlement.tier,
            "subject_id": entitlement.subject_id,
            "billing_subject": entitlement.billing_subject or "",
            "source": entitlement.source,
        },
    )


@router.get("/queue/history", response_model=WorkflowQueueHistoryResponse)
def list_queue_jobs_endpoint(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    team_subject: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> WorkflowQueueHistoryResponse:
    return list_queue_jobs(db, status=status, team_subject=team_subject, limit=limit)


@router.get("/queue/{job_id}", response_model=WorkflowQueueJobRead)
def get_queue_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
) -> WorkflowQueueJobRead:
    return get_queue_job(db, job_id)


@router.post("/queue/{job_id}/retry", response_model=WorkflowQueueRunResponse)
def retry_queue_job_endpoint(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: str | None = Query(default=None),
) -> WorkflowQueueRunResponse:
    return retry_queue_job(db, job_id, background_tasks, actor=actor)


@router.post("/queue/{job_id}/cancel", response_model=WorkflowQueueJobRead)
def cancel_queue_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    actor: str | None = Query(default=None),
) -> WorkflowQueueJobRead:
    return cancel_queue_job(db, job_id, actor=actor)


@router.get("/{orchestration_id}/history-events", response_model=HistoryIntegrityResponse)
def get_orchestration_history_events_endpoint(
    orchestration_id: int,
    db: Session = Depends(get_db),
) -> HistoryIntegrityResponse:
    get_orchestration(db, orchestration_id)
    return HistoryIntegrityResponse.model_validate(verify_orchestration_history(db, orchestration_id))


@router.get("/{orchestration_id}/checkpoints", response_model=WorkflowCheckpointHistoryResponse)
def get_orchestration_checkpoints_endpoint(
    orchestration_id: int,
    db: Session = Depends(get_db),
) -> WorkflowCheckpointHistoryResponse:
    return get_orchestration_checkpoints(db, orchestration_id)


@router.get("/{orchestration_id}/evidence", response_model=WorkflowEvidenceExportResponse)
def get_orchestration_evidence_export_endpoint(
    orchestration_id: int,
    db: Session = Depends(get_db),
) -> WorkflowEvidenceExportResponse:
    return get_orchestration_evidence_export(db, orchestration_id)


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


@router.get("/templates/init/json", response_model=list[WorkflowTemplateCreate])
def get_workflow_template_init_json() -> list[WorkflowTemplateCreate]:
    return load_builtin_workflow_templates()


@router.post("/templates/import/builtin", response_model=WorkflowTemplateImportResponse)
def import_builtin_workflow_templates_endpoint(
    db: Session = Depends(get_db),
) -> WorkflowTemplateImportResponse:
    return import_builtin_workflow_templates(db)


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
