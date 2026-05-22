import json
import logging
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import quantiles

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, load_only

from app.models import (
    AgentRunLog,
    NoteEntry,
    PromptTemplate,
    WorkflowCheckpoint,
    WorkflowOrchestration,
    WorkflowQueueJob,
    WorkflowStepRun,
    WorkflowTemplate,
)
from app.schemas import (
    DailyContextInput,
    DailyReflectionInput,
    HistoryIntegritySummary,
    StepStatus,
    SubscriptionTier,
    TechnicalAnalysisInput,
    WorkflowAuditBlock,
    WorkflowCheckpointHistoryResponse,
    WorkflowOrchestrationHistoryResponse,
    WorkflowOrchestrationMetricsResponse,
    WorkflowOrchestrationRead,
    WorkflowOrchestrationRunRequest,
    WorkflowOrchestrationSummary,
    WorkflowStepDefinition,
    WorkflowStepRunRead,
    WorkflowTemplateCreate,
    WorkflowTemplateImportRequest,
    WorkflowTemplateImportResponse,
    WorkflowTemplatePolicy,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from app.services.agent_log_service import log_agent_action
from app.services.entitlement_service import capability_policy_for_tier, quota_policy_for_tier
from app.services.history_ledger import (
    append_monetization_event,
    append_orchestration_accepted_event,
    append_orchestration_completed_event,
    append_step_event,
    summarize_orchestration_histories,
)
from app.services.monetization_service import (
    get_plan_usage_quota,
    record_plan_usage,
    usage_metric_for_endpoint,
)
from app.services.workflow_checkpoints import (
    append_orchestration_checkpoint,
    list_checkpoints_for_orchestration,
    summarize_checkpoint_counts,
    to_checkpoint_read,
)
from app.time_utils import utcnow_naive

logger = logging.getLogger(__name__)

DEFAULT_STEPS = [
    WorkflowStepDefinition(step_name="Plan The Day", agent_type="planner", enabled=True),
    WorkflowStepDefinition(step_name="Analyze Technical Signals", agent_type="analyzer", enabled=True),
    WorkflowStepDefinition(step_name="Review And Reflect", agent_type="reviewer", enabled=True),
]
BUILTIN_WORKFLOW_TEMPLATES_PATH = Path(__file__).resolve().parents[1] / "bootstrap" / "workflow_templates_v1.json"
TIER_RANK = {"free": 0, "pro": 1, "power": 2}
VALID_TEMPLATE_RISKS = {"low", "medium", "high", "critical"}


def _utcnow() -> datetime:
    return utcnow_naive()


def normalize_tier(value: str) -> SubscriptionTier:
    normalized = value.strip().lower()
    if normalized not in {"free", "pro", "power"}:
        return "pro"
    return normalized  # type: ignore[return-value]


def run_orchestration(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    subscription_tier: str,
    should_cancel: Callable[[], bool] | None = None,
    monetization_context: dict[str, str | int] | None = None,
) -> WorkflowOrchestrationRead:
    tier = normalize_tier(subscription_tier)
    steps = _resolve_steps(db, payload)
    active_steps = [step for step in steps if step.enabled]

    policy = capability_policy_for_tier(tier)
    max_enabled_steps = int(policy["max_enabled_steps"])
    if len(active_steps) > max_enabled_steps:
        raise _monetization_error(
            code="upgrade_required",
            status_code=403,
            message=f"Tier '{tier}' supports at most {max_enabled_steps} enabled step(s).",
            current_tier=tier,
            required_tier=str(policy["required_tier_for_multi_step"]),
            capability="multi_step_workflow",
            endpoint="/api/orchestrations/run",
        )

    started = _utcnow()
    request_dump = payload.model_dump(mode="json")
    trust_metadata = _trust_metadata_from_payload(payload)
    record = WorkflowOrchestration(
        status="running",
        duration_ms=0,
        entry_source=payload.entry_source.strip() or "manual",
        subscription_tier=tier,
        team_subject=trust_metadata["team_subject"],
        requested_by=trust_metadata["requested_by"],
        approval_actor=trust_metadata["approval_actor"],
        approval_note=trust_metadata["approval_note"],
        request_json=json.dumps(request_dump),
        result_json="{}",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    append_orchestration_accepted_event(db, record, request_dump)
    append_orchestration_checkpoint(
        db,
        record,
        checkpoint_type="orchestration.accepted",
        payload={
            "request": request_dump,
            "active_steps": len(active_steps),
            "subscription_tier": tier,
        },
        occurred_at=record.created_at,
        uid_hint="accepted",
    )

    log_agent_action(
        db,
        task_type="workflow_orchestration_request",
        input_summary=json.dumps(
            {
                "id": record.id,
                "tier": tier,
                "steps": len(active_steps),
                "team_subject": record.team_subject,
                "requested_by": record.requested_by,
            }
        ),
        output_summary="orchestration accepted",
        status="received",
    )

    step_records: list[WorkflowStepRun] = []
    previous_audits: list[WorkflowAuditBlock] = []
    has_failure = False

    for step_index, step in enumerate(active_steps, start=1):
        if should_cancel and should_cancel():
            has_failure = True
            step_started = _utcnow()
            step_finished = _utcnow()
            append_orchestration_checkpoint(
                db,
                record,
                checkpoint_type="step.started",
                status="running",
                payload={
                    "step_name": step.step_name,
                    "agent_type": step.agent_type,
                    "cancel_requested": True,
                    "message": "Step canceled before execution.",
                },
                step_name=step.step_name,
                step_index=step_index,
                occurred_at=step_started,
                uid_hint=f"step:{step_index}:started:canceled",
            )
            canceled_audit = WorkflowAuditBlock(
                conclusion=f"Step '{step.step_name}' canceled before execution.",
                evidence="Queue cancel_requested flag was true before step execution.",
                risk="Workflow output may be incomplete due to cancellation.",
                next_action="Retry the workflow run when ready.",
            )
            step_record = WorkflowStepRun(
                orchestration_id=record.id,
                step_name=step.step_name,
                agent_type=step.agent_type,
                status="skipped",
                input_summary="{}",
                output_summary=canceled_audit.conclusion,
                audit_json=json.dumps(canceled_audit.model_dump(mode="json")),
                fallback_action="Run queue retry when cancellation is no longer required.",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=0,
            )
            db.add(step_record)
            db.commit()
            db.refresh(step_record)
            append_step_event(db, step_record)
            append_orchestration_checkpoint(
                db,
                record,
                checkpoint_type="step.skipped",
                status="skipped",
                payload={
                    "step_id": step_record.id,
                    "step_name": step.step_name,
                    "agent_type": step.agent_type,
                    "audit": canceled_audit.model_dump(mode="json"),
                    "fallback_action": step_record.fallback_action,
                },
                step_name=step.step_name,
                step_index=step_index,
                occurred_at=step_finished,
                uid_hint=f"step:{step_record.id}:skipped",
            )
            step_records.append(step_record)
            previous_audits.append(canceled_audit)
            break

        step_started = _utcnow()
        step_input = _build_step_input(step.agent_type, payload, previous_audits)
        append_orchestration_checkpoint(
            db,
            record,
            checkpoint_type="step.started",
            status="running",
            payload={
                "step_name": step.step_name,
                "agent_type": step.agent_type,
                "input": _safe_json_dict(step_input),
            },
            step_name=step.step_name,
            step_index=step_index,
            occurred_at=step_started,
            uid_hint=f"step:{step_index}:started",
        )
        audit, step_status, fallback = _execute_step(step.agent_type, payload, previous_audits)
        step_finished = _utcnow()

        if step_status == "failed":
            has_failure = True

        step_record = WorkflowStepRun(
            orchestration_id=record.id,
            step_name=step.step_name,
            agent_type=step.agent_type,
            status=step_status,
            input_summary=step_input,
            output_summary=audit.conclusion,
            audit_json=json.dumps(audit.model_dump(mode="json")),
            fallback_action=fallback,
            started_at=step_started,
            finished_at=step_finished,
            duration_ms=max(0, int((step_finished - step_started).total_seconds() * 1000)),
        )
        db.add(step_record)
        db.commit()
        db.refresh(step_record)
        append_step_event(db, step_record)
        append_orchestration_checkpoint(
            db,
            record,
            checkpoint_type=f"step.{step_status}",
            status=step_status,
            payload={
                "step_id": step_record.id,
                "step_name": step.step_name,
                "agent_type": step.agent_type,
                "output_summary": step_record.output_summary,
                "audit": audit.model_dump(mode="json"),
                "fallback_action": fallback,
                "duration_ms": step_record.duration_ms,
            },
            step_name=step.step_name,
            step_index=step_index,
            occurred_at=step_finished,
            uid_hint=f"step:{step_record.id}:{step_status}",
        )
        step_records.append(step_record)
        previous_audits.append(audit)

    finished = _utcnow()
    summary = _compose_summary(previous_audits)
    status = "partial_success" if has_failure else "success"
    record.status = status
    record.duration_ms = max(0, int((finished - started).total_seconds() * 1000))
    record.result_json = json.dumps(summary.model_dump(mode="json"))
    record.updated_at = finished
    db.add(record)
    db.commit()
    db.refresh(record)
    append_orchestration_completed_event(
        db,
        record,
        summary=summary.model_dump(mode="json"),
        step_count=len(step_records),
    )
    append_orchestration_checkpoint(
        db,
        record,
        checkpoint_type=f"orchestration.{status}",
        payload={
            "summary": summary.model_dump(mode="json"),
            "step_count": len(step_records),
            "duration_ms": record.duration_ms,
        },
        occurred_at=record.updated_at,
        uid_hint=f"completed:{status}",
    )

    _persist_reusable_assets(db, record, summary, payload)
    log_agent_action(
        db,
        task_type="workflow_orchestration_completed",
        input_summary=f"orchestration_id={record.id}",
        output_summary=summary.conclusion,
        status=status,
    )
    if monetization_context is not None:
        _write_monetization_event(
            db,
            event_name="monetization.usage_recorded",
            status="success",
            payload={
                "endpoint": str(monetization_context.get("endpoint", "/api/orchestrations/run")),
                "tier": tier,
                "subject_id": str(monetization_context.get("subject_id", "unknown")),
                "billing_subject": str(monetization_context.get("billing_subject", "")),
                "orchestration_id": record.id,
            },
            outcome="usage recorded after workflow execution",
        )
    return _to_orchestration_read(record, step_records, summary, checkpoint_count=2 + len(step_records) * 2)


def enforce_monetization_policy_for_run(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    tier: str,
    subject_id: str,
    endpoint: str,
    billing_subject: str | None = None,
) -> dict[str, int]:
    normalized_tier = normalize_tier(tier)
    template = _resolve_template(db, payload)
    template_policy = _template_policy_from_record(template) if template is not None else None
    if template is not None and template_policy is not None:
        _enforce_template_policy(
            db,
            payload,
            template=template,
            policy=template_policy,
            tier=normalized_tier,
            subject_id=subject_id,
            endpoint=endpoint,
        )
    capability_policy = capability_policy_for_tier(normalized_tier)
    max_enabled_steps = int(capability_policy["max_enabled_steps"])
    active_steps = [step for step in _resolve_steps(db, payload) if step.enabled]
    if len(active_steps) > max_enabled_steps:
        _write_monetization_event(
            db,
            event_name="monetization.capability_blocked_upgrade_required",
            status="blocked",
            payload={
                "endpoint": endpoint,
                "tier": normalized_tier,
                "subject_id": subject_id,
                "capability": "multi_step_workflow",
                "active_steps": len(active_steps),
                "max_enabled_steps": max_enabled_steps,
                "required_tier": str(capability_policy["required_tier_for_multi_step"]),
            },
            outcome="capability blocked",
        )
        raise _monetization_error(
            code="upgrade_required",
            status_code=403,
            message=(
                f"Tier '{normalized_tier}' supports at most {max_enabled_steps} enabled step(s). "
                "Upgrade to continue."
            ),
            current_tier=normalized_tier,
            required_tier=str(capability_policy["required_tier_for_multi_step"]),
            capability="multi_step_workflow",
            endpoint=endpoint,
        )
    _write_monetization_event(
        db,
        event_name="monetization.capability_checked",
        status="allowed",
        payload={
            "endpoint": endpoint,
            "tier": normalized_tier,
            "subject_id": subject_id,
            "active_steps": len(active_steps),
            "max_enabled_steps": max_enabled_steps,
        },
        outcome="capability allowed",
    )

    quota_policy = quota_policy_for_tier(normalized_tier)
    window_days = int(quota_policy["window_days"])
    limit = int(quota_policy["max_runs"])
    usage_metric = usage_metric_for_endpoint(endpoint)
    plan_quota = get_plan_usage_quota(db, subject=billing_subject, metric=usage_metric)
    if plan_quota is not None:
        used = int(plan_quota["used"])
        plan_limit = int(plan_quota["limit"])
        if used >= plan_limit:
            _write_monetization_event(
                db,
                event_name="monetization.quota_exceeded",
                status="blocked",
                payload={
                    "endpoint": endpoint,
                    "tier": normalized_tier,
                    "subject_id": subject_id,
                    "billing_subject": billing_subject or "",
                    "window": "billing_period",
                    "metric": str(plan_quota["metric"]),
                    "period_start": str(plan_quota["period_start"]),
                    "period_end": str(plan_quota["period_end"]),
                    "limit": plan_limit,
                    "used": used,
                },
                outcome="billing period quota exceeded",
            )
            raise _monetization_error(
                code="quota_exceeded",
                status_code=429,
                message=f"Quota exceeded for tier '{normalized_tier}'.",
                tier=normalized_tier,
                endpoint=endpoint,
                quota={
                    "window": "billing_period",
                    "metric": str(plan_quota["metric"]),
                    "period_start": str(plan_quota["period_start"]),
                    "period_end": str(plan_quota["period_end"]),
                    "limit": plan_limit,
                    "used": used,
                },
            )
        _write_monetization_event(
            db,
            event_name="monetization.quota_checked",
            status="allowed",
            payload={
                "endpoint": endpoint,
                "tier": normalized_tier,
                "subject_id": subject_id,
                "billing_subject": billing_subject or "",
                "window": "billing_period",
                "metric": str(plan_quota["metric"]),
                "period_start": str(plan_quota["period_start"]),
                "period_end": str(plan_quota["period_end"]),
                "limit": plan_limit,
                "used": used,
            },
            outcome="billing period quota allowed",
        )
        return {"window_days": window_days, "limit": plan_limit, "used": used}

    used = _count_usage_events(db, endpoint=endpoint, subject_id=subject_id, window_days=window_days)
    if used >= limit:
        _write_monetization_event(
            db,
            event_name="monetization.quota_exceeded",
            status="blocked",
            payload={
                "endpoint": endpoint,
                "tier": normalized_tier,
                "subject_id": subject_id,
                "window_days": window_days,
                "limit": limit,
                "used": used,
            },
            outcome="quota exceeded",
        )
        raise _monetization_error(
            code="quota_exceeded",
            status_code=429,
            message=f"Quota exceeded for tier '{normalized_tier}'.",
            tier=normalized_tier,
            endpoint=endpoint,
            quota={"window_days": window_days, "limit": limit, "used": used},
        )
    _write_monetization_event(
        db,
        event_name="monetization.quota_checked",
        status="allowed",
        payload={
            "endpoint": endpoint,
            "tier": normalized_tier,
            "subject_id": subject_id,
            "window_days": window_days,
            "limit": limit,
            "used": used,
        },
        outcome="quota allowed",
    )
    return {"window_days": window_days, "limit": limit, "used": used}


def list_orchestrations(
    db: Session,
    *,
    status: str | None = None,
    subscription_tier: str | None = None,
    limit: int = 50,
    include_steps: bool = True,
    include_integrity: bool = True,
    team_subject: str | None = None,
) -> WorkflowOrchestrationHistoryResponse:
    safe_limit = max(1, min(limit, 200))
    query = db.query(WorkflowOrchestration).options(
        load_only(
            WorkflowOrchestration.id,
            WorkflowOrchestration.status,
            WorkflowOrchestration.duration_ms,
            WorkflowOrchestration.entry_source,
            WorkflowOrchestration.subscription_tier,
            WorkflowOrchestration.team_subject,
            WorkflowOrchestration.requested_by,
            WorkflowOrchestration.approval_actor,
            WorkflowOrchestration.approval_note,
            WorkflowOrchestration.result_json,
            WorkflowOrchestration.created_at,
            WorkflowOrchestration.updated_at,
        )
    )
    if status:
        query = query.filter(WorkflowOrchestration.status == status.strip().lower())
    if subscription_tier:
        query = query.filter(WorkflowOrchestration.subscription_tier == normalize_tier(subscription_tier))
    if team_subject and team_subject.strip():
        query = query.filter(WorkflowOrchestration.team_subject == team_subject.strip())
    records = (
        query.order_by(WorkflowOrchestration.created_at.desc(), WorkflowOrchestration.id.desc())
        .limit(safe_limit)
        .all()
    )

    steps_by_orchestration_id: dict[int, list[WorkflowStepRun]] = defaultdict(list)
    if include_steps and records:
        orchestration_ids = [record.id for record in records]
        step_records = (
            db.query(WorkflowStepRun)
            .filter(WorkflowStepRun.orchestration_id.in_(orchestration_ids))
            .order_by(WorkflowStepRun.orchestration_id.asc(), WorkflowStepRun.id.asc())
            .all()
        )
        for step in step_records:
            steps_by_orchestration_id[step.orchestration_id].append(step)

    integrity_by_orchestration_id: dict[int, HistoryIntegritySummary] = {}
    if include_integrity and records:
        raw_integrity = summarize_orchestration_histories(db, [record.id for record in records])
        integrity_by_orchestration_id = {
            orchestration_id: HistoryIntegritySummary.model_validate(summary)
            for orchestration_id, summary in raw_integrity.items()
        }

    checkpoint_counts = summarize_checkpoint_counts(db, [record.id for record in records]) if records else {}

    items = []
    for record in records:
        steps = steps_by_orchestration_id.get(record.id, [])
        summary = _safe_orchestration_summary(record)
        items.append(
            _to_orchestration_read(
                record,
                steps,
                summary,
                ledger_integrity=integrity_by_orchestration_id.get(record.id),
                checkpoint_count=checkpoint_counts.get(record.id, 0),
            )
        )
    return WorkflowOrchestrationHistoryResponse(items=items)


def get_orchestration_metrics(db: Session, *, days: int = 7) -> WorkflowOrchestrationMetricsResponse:
    period_days = max(1, min(days, 90))
    window_start = _utcnow() - timedelta(days=period_days)
    total_runs, partial_count, average_duration = (
        db.query(
            func.count(WorkflowOrchestration.id),
            func.coalesce(
                func.sum(case((WorkflowOrchestration.status == "partial_success", 1), else_=0)),
                0,
            ),
            func.coalesce(func.avg(WorkflowOrchestration.duration_ms), 0),
        )
        .filter(WorkflowOrchestration.created_at >= window_start)
        .one()
    )
    total_runs = int(total_runs or 0)
    partial_count = int(partial_count or 0)
    average_duration_ms = int(average_duration or 0)
    partial_success_rate = round((partial_count / total_runs), 4) if total_runs > 0 else 0.0
    metric_records = (
        db.query(
            WorkflowOrchestration.status,
            WorkflowOrchestration.request_json,
        )
        .filter(WorkflowOrchestration.created_at >= window_start)
        .all()
    )
    template_ids = {
        template_id
        for _status, request_json in metric_records
        for template_id in [_template_id_from_request_json(request_json)]
        if template_id is not None
    }
    templates_by_id = {
        template.id: template
        for template in (
            db.query(WorkflowTemplate).filter(WorkflowTemplate.id.in_(template_ids)).all()
            if template_ids
            else []
        )
    }
    billable_work_units = sum(
        _billable_work_units_from_request_json(request_json, templates_by_id)
        for _status, request_json in metric_records
    )
    successful_audited_workflows = len(
        [status for status, _request_json in metric_records if status in {"success", "partial_success"}]
    )
    approval_required_blocks = _count_monetization_logs(
        db,
        task_type="monetization.approval_required_blocked",
        window_start=window_start,
    )
    template_policy_upgrade_blocks = _count_monetization_logs(
        db,
        task_type="monetization.template_policy_upgrade_required",
        window_start=window_start,
    )
    approved_runs = int(
        db.query(func.count(WorkflowOrchestration.id))
        .filter(
            WorkflowOrchestration.created_at >= window_start,
            WorkflowOrchestration.approval_actor != "",
        )
        .scalar()
        or 0
    )
    checkpointed_runs = int(
        db.query(func.count(func.distinct(WorkflowCheckpoint.orchestration_id)))
        .filter(
            WorkflowCheckpoint.created_at >= window_start,
            WorkflowCheckpoint.orchestration_id.isnot(None),
        )
        .scalar()
        or 0
    )
    failed_jobs_needing_owner = int(
        db.query(func.count(WorkflowQueueJob.id))
        .filter(
            WorkflowQueueJob.updated_at >= window_start,
            WorkflowQueueJob.status == "failed",
        )
        .scalar()
        or 0
    )

    return WorkflowOrchestrationMetricsResponse(
        period_days=period_days,
        total_runs=total_runs,
        weekly_active_orchestrations=total_runs,
        partial_success_rate=partial_success_rate,
        average_duration_ms=average_duration_ms,
        billable_work_units=billable_work_units,
        successful_audited_workflows=successful_audited_workflows,
        approval_required_blocks=approval_required_blocks,
        template_policy_upgrade_blocks=template_policy_upgrade_blocks,
        approved_runs=approved_runs,
        checkpointed_runs=checkpointed_runs,
        failed_jobs_needing_owner=failed_jobs_needing_owner,
    )


def get_orchestration(db: Session, orchestration_id: int) -> WorkflowOrchestrationRead:
    record = db.query(WorkflowOrchestration).filter(WorkflowOrchestration.id == orchestration_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Orchestration not found.")
    steps = (
        db.query(WorkflowStepRun)
        .filter(WorkflowStepRun.orchestration_id == orchestration_id)
        .order_by(WorkflowStepRun.id.asc())
        .all()
    )
    summary = _safe_orchestration_summary(record)
    checkpoint_counts = summarize_checkpoint_counts(db, [record.id])
    return _to_orchestration_read(record, steps, summary, checkpoint_count=checkpoint_counts.get(record.id, 0))


def get_orchestration_checkpoints(db: Session, orchestration_id: int) -> WorkflowCheckpointHistoryResponse:
    get_orchestration(db, orchestration_id)
    checkpoints = list_checkpoints_for_orchestration(db, orchestration_id)
    return WorkflowCheckpointHistoryResponse(items=[to_checkpoint_read(checkpoint) for checkpoint in checkpoints])


def get_monetization_observability(db: Session, *, days: int = 7) -> dict[str, object]:
    period_days = 30 if int(days) == 30 else 7
    window_start = _utcnow() - timedelta(days=period_days)

    try:
        records = (
            db.query(WorkflowOrchestration)
            .filter(WorkflowOrchestration.created_at >= window_start)
            .all()
        )
    except SQLAlchemyError:
        records = []
    runs_by_tier = {"free": 0, "pro": 0, "power": 0}
    for row in records:
        tier = normalize_tier(row.subscription_tier)
        runs_by_tier[tier] = runs_by_tier.get(tier, 0) + 1

    try:
        monetization_logs = (
            db.query(AgentRunLog)
            .filter(
                AgentRunLog.task_type.like("monetization.%"),
                AgentRunLog.created_at >= window_start,
            )
            .all()
        )
    except SQLAlchemyError:
        monetization_logs = []

    usage_logs = [row for row in monetization_logs if row.task_type == "monetization.usage_recorded"]
    active_subjects = set()
    for row in usage_logs:
        payload = _safe_json_dict(row.input_summary)
        subject_id = payload.get("subject_id")
        if isinstance(subject_id, str) and subject_id:
            active_subjects.add(subject_id)

    quota_checks = [row for row in monetization_logs if row.task_type == "monetization.quota_checked"]
    quota_hits = [row for row in monetization_logs if row.task_type == "monetization.quota_exceeded"]
    quota_denominator = len(quota_checks) + len(quota_hits)
    quota_hit_rate = round(len(quota_hits) / quota_denominator, 4) if quota_denominator > 0 else 0.0

    upgrade_intent_count = len(
        [row for row in monetization_logs if row.task_type == "monetization.capability_blocked_upgrade_required"]
    )

    try:
        queue_jobs = (
            db.query(WorkflowQueueJob)
            .filter(WorkflowQueueJob.created_at >= window_start)
            .all()
        )
    except SQLAlchemyError:
        queue_jobs = []
    queue_terminal = [job for job in queue_jobs if job.status in {"succeeded", "failed", "canceled"}]
    queue_succeeded = [job for job in queue_terminal if job.status == "succeeded"]
    queue_success_rate = (
        round(len(queue_succeeded) / len(queue_terminal), 4) if len(queue_terminal) > 0 else 0.0
    )

    queue_latencies = [
        max(0, int((job.updated_at - job.created_at).total_seconds() * 1000))
        for job in queue_terminal
    ]
    p95_queue_latency_ms = _p95(queue_latencies)

    reasons: dict[str, int] = {}
    for job in queue_terminal:
        if job.status not in {"failed", "canceled"}:
            continue
        reason = (job.error_message or f"queue_{job.status}").strip()
        if not reason:
            reason = f"queue_{job.status}"
        reasons[reason] = reasons.get(reason, 0) + 1
    top_failure_reasons = [
        {"reason": reason, "count": count}
        for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    return {
        "period_days": period_days,
        "active_subjects": len(active_subjects),
        "runs_by_tier": runs_by_tier,
        "quota_hit_rate": quota_hit_rate,
        "upgrade_intent_count": upgrade_intent_count,
        "queue_success_rate": queue_success_rate,
        "p95_queue_latency_ms": p95_queue_latency_ms,
        "top_failure_reasons": top_failure_reasons,
    }


def create_workflow_template(db: Session, payload: WorkflowTemplateCreate) -> WorkflowTemplateRead:
    tags = _tags_with_policy(payload.tags, payload.policy, payload.steps)
    record = WorkflowTemplate(
        name=payload.name.strip(),
        description=payload.description.strip(),
        steps_json=json.dumps([step.model_dump(mode="json") for step in payload.steps]),
        tags_json=json.dumps(tags),
        enabled=payload.enabled,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_template_read(record)


def update_workflow_template(
    db: Session,
    template_id: int,
    payload: WorkflowTemplateUpdate,
) -> WorkflowTemplateRead:
    record = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow template not found.")

    if payload.name is not None:
        record.name = payload.name.strip()
    if payload.description is not None:
        record.description = payload.description.strip()
    if payload.steps is not None:
        record.steps_json = json.dumps([step.model_dump(mode="json") for step in payload.steps])
    if payload.tags is not None or payload.policy is not None or payload.steps is not None:
        next_steps = (
            payload.steps
            if payload.steps is not None
            else [WorkflowStepDefinition.model_validate(item) for item in json.loads(record.steps_json or "[]")]
        )
        next_tags = payload.tags if payload.tags is not None else _normalize_tags(json.loads(record.tags_json or "[]"))
        existing_policy = _template_policy_from_tags(next_tags, next_steps)
        record.tags_json = json.dumps(_tags_with_policy(next_tags, payload.policy or existing_policy, next_steps))
    if payload.enabled is not None:
        record.enabled = payload.enabled

    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_template_read(record)


def list_workflow_templates(db: Session, *, enabled: bool | None = None) -> list[WorkflowTemplateRead]:
    query = db.query(WorkflowTemplate)
    if enabled is not None:
        query = query.filter(WorkflowTemplate.enabled == enabled)
    records = query.order_by(WorkflowTemplate.updated_at.desc(), WorkflowTemplate.id.desc()).all()
    return [_to_template_read(record) for record in records]


def export_workflow_templates(db: Session) -> list[WorkflowTemplateRead]:
    return list_workflow_templates(db)


def load_builtin_workflow_templates() -> list[WorkflowTemplateCreate]:
    raw = json.loads(BUILTIN_WORKFLOW_TEMPLATES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("Workflow template bootstrap file must contain a list.")
    templates = [WorkflowTemplateCreate.model_validate(item) for item in raw]
    return [
        template.model_copy(update={"policy": template.policy or _template_policy_from_tags(template.tags, template.steps)})
        for template in templates
    ]


def import_builtin_workflow_templates(db: Session) -> WorkflowTemplateImportResponse:
    return import_workflow_templates(
        db,
        WorkflowTemplateImportRequest(
            items=load_builtin_workflow_templates(),
            upsert_by_name=True,
        ),
    )


def import_workflow_templates(db: Session, payload: WorkflowTemplateImportRequest) -> WorkflowTemplateImportResponse:
    imported = 0
    updated = 0
    skipped = 0
    for item in payload.items:
        matched = None
        if payload.upsert_by_name:
            matched = db.query(WorkflowTemplate).filter(WorkflowTemplate.name == item.name.strip()).first()
        if matched:
            matched.description = item.description.strip()
            matched.steps_json = json.dumps([step.model_dump(mode="json") for step in item.steps])
            matched.tags_json = json.dumps(_tags_with_policy(item.tags, item.policy, item.steps))
            matched.enabled = item.enabled
            db.add(matched)
            updated += 1
            continue
        record = WorkflowTemplate(
            name=item.name.strip(),
            description=item.description.strip(),
            steps_json=json.dumps([step.model_dump(mode="json") for step in item.steps]),
            tags_json=json.dumps(_tags_with_policy(item.tags, item.policy, item.steps)),
            enabled=item.enabled,
        )
        db.add(record)
        imported += 1

    db.commit()
    total = len(payload.items)
    if imported + updated < total:
        skipped = total - imported - updated
    return WorkflowTemplateImportResponse(imported=imported, updated=updated, skipped=skipped, total=total)


def _resolve_template(db: Session, payload: WorkflowOrchestrationRunRequest) -> WorkflowTemplate | None:
    if payload.template_id is None:
        return None
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == payload.template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Workflow template not found.")
    return template


def _resolve_steps(db: Session, payload: WorkflowOrchestrationRunRequest) -> list[WorkflowStepDefinition]:
    template = _resolve_template(db, payload)
    if template is not None:
        return [WorkflowStepDefinition.model_validate(item) for item in json.loads(template.steps_json or "[]")]
    if payload.steps:
        return payload.steps
    return DEFAULT_STEPS


def _enforce_template_policy(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    template: WorkflowTemplate,
    policy: WorkflowTemplatePolicy,
    tier: SubscriptionTier,
    subject_id: str,
    endpoint: str,
) -> None:
    if TIER_RANK[tier] < TIER_RANK[policy.required_tier]:
        _write_monetization_event(
            db,
            event_name="monetization.template_policy_upgrade_required",
            status="blocked",
            payload={
                "endpoint": endpoint,
                "tier": tier,
                "subject_id": subject_id,
                "template_id": template.id,
                "template_name": template.name,
                "required_tier": policy.required_tier,
                "risk_level": policy.risk_level,
            },
            outcome="template policy tier blocked",
        )
        raise _monetization_error(
            code="upgrade_required",
            status_code=403,
            message=f"Template '{template.name}' requires tier '{policy.required_tier}'.",
            current_tier=tier,
            required_tier=policy.required_tier,
            capability="template_policy",
            endpoint=endpoint,
            template_id=template.id,
            risk_level=policy.risk_level,
        )
    if policy.approval_required and not payload.approval_confirmed:
        _write_monetization_event(
            db,
            event_name="monetization.approval_required_blocked",
            status="blocked",
            payload={
                "endpoint": endpoint,
                "tier": tier,
                "subject_id": subject_id,
                "template_id": template.id,
                "template_name": template.name,
                "risk_level": policy.risk_level,
                "allowed_tool_scopes": policy.allowed_tool_scopes,
            },
            outcome="human approval required",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "code": "approval_required",
                "message": f"Template '{template.name}' requires explicit human approval.",
                "template_id": template.id,
                "template_name": template.name,
                "risk_level": policy.risk_level,
                "required_tier": policy.required_tier,
                "allowed_tool_scopes": policy.allowed_tool_scopes,
            },
        )
    if policy.approval_required:
        _write_monetization_event(
            db,
            event_name="monetization.approval_confirmed",
            status="allowed",
            payload={
                "endpoint": endpoint,
                "tier": tier,
                "subject_id": subject_id,
                "template_id": template.id,
                "template_name": template.name,
                "risk_level": policy.risk_level,
            },
            outcome="human approval confirmed",
        )


def _template_policy_from_record(template: WorkflowTemplate) -> WorkflowTemplatePolicy:
    return _template_policy_from_tags(
        _normalize_tags(json.loads(template.tags_json or "[]")),
        [WorkflowStepDefinition.model_validate(item) for item in json.loads(template.steps_json or "[]")],
    )


def _template_policy_from_tags(tags: list[str], steps: list[WorkflowStepDefinition]) -> WorkflowTemplatePolicy:
    normalized = _normalize_tags(tags)
    active_step_count = len([step for step in steps if step.enabled])
    required_tier = _tag_value(normalized, "tier")
    risk_level = _tag_value(normalized, "risk")
    work_units = _int_tag_value(normalized, "work-units")
    tool_scopes = [tag.split(":", 1)[1] for tag in normalized if tag.startswith("tool:") and tag.split(":", 1)[1]]
    return WorkflowTemplatePolicy(
        required_tier=normalize_tier(required_tier or "pro"),
        risk_level=(risk_level if risk_level in VALID_TEMPLATE_RISKS else "medium"),  # type: ignore[arg-type]
        approval_required="approval:required" in normalized,
        allowed_tool_scopes=tool_scopes or ["none"],
        billable_work_units=work_units or max(1, active_step_count),
    )


def _tags_with_policy(
    tags: list[str],
    policy: WorkflowTemplatePolicy | None,
    steps: list[WorkflowStepDefinition],
) -> list[str]:
    normalized = [
        tag
        for tag in _normalize_tags(tags)
        if not (
            tag.startswith("tier:")
            or tag.startswith("risk:")
            or tag.startswith("tool:")
            or tag.startswith("work-units:")
            or tag.startswith("approval:")
        )
    ]
    resolved_policy = policy or _template_policy_from_tags(tags, steps)
    policy_tags = [
        f"tier:{resolved_policy.required_tier}",
        f"risk:{resolved_policy.risk_level}",
        "approval:required" if resolved_policy.approval_required else "approval:none",
        f"work-units:{resolved_policy.billable_work_units}",
    ]
    policy_tags.extend(f"tool:{scope}" for scope in resolved_policy.allowed_tool_scopes)
    return _normalize_tags([*normalized, *policy_tags])


def _tag_value(tags: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for tag in tags:
        if tag.startswith(prefix):
            return tag.split(":", 1)[1].strip()
    return None


def _int_tag_value(tags: list[str], key: str) -> int | None:
    value = _tag_value(tags, key)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _template_id_from_request_json(value: str) -> int | None:
    payload = _safe_json_dict(value)
    template_id = payload.get("template_id")
    if isinstance(template_id, int):
        return template_id
    return None


def _billable_work_units_from_request_json(value: str, templates_by_id: dict[int, WorkflowTemplate]) -> int:
    payload = _safe_json_dict(value)
    template_id = payload.get("template_id")
    if isinstance(template_id, int) and template_id in templates_by_id:
        return _template_policy_from_record(templates_by_id[template_id]).billable_work_units
    steps = payload.get("steps")
    if isinstance(steps, list):
        active_steps = len([step for step in steps if isinstance(step, dict) and step.get("enabled", True)])
        return max(1, active_steps)
    return 1


def _count_monetization_logs(db: Session, *, task_type: str, window_start: datetime) -> int:
    return int(
        db.query(func.count(AgentRunLog.id))
        .filter(
            AgentRunLog.task_type == task_type,
            AgentRunLog.created_at >= window_start,
        )
        .scalar()
        or 0
    )


def _build_step_input(
    agent_type: str,
    payload: WorkflowOrchestrationRunRequest,
    previous_audits: list[WorkflowAuditBlock],
) -> str:
    if agent_type == "planner":
        context = payload.daily_context or DailyContextInput(tasks=[], meetings=[], blockers=[], priorities=[])
        return json.dumps(context.model_dump(mode="json"))
    if agent_type == "analyzer":
        context = payload.technical_input
        context_dump = (
            context.model_dump(mode="json")
            if context is not None
            else {"logs": "", "errors": [], "code_snippets": [], "issue_description": ""}
        )
        return json.dumps(
            {
                "technical_input": context_dump,
                "planner_conclusion": previous_audits[-1].conclusion if previous_audits else "",
            }
        )
    context = payload.reflection_input or DailyReflectionInput(
        completed=[],
        unfinished=[],
        blockers=[],
        mood_or_notes="",
    )
    return json.dumps(
        {
            "reflection_input": context.model_dump(mode="json"),
            "upstream_signals": [audit.conclusion for audit in previous_audits],
        }
    )


def _execute_step(
    agent_type: str,
    payload: WorkflowOrchestrationRunRequest,
    previous_audits: list[WorkflowAuditBlock],
) -> tuple[WorkflowAuditBlock, StepStatus, str]:
    if agent_type == "planner":
        context = payload.daily_context or DailyContextInput(tasks=[], meetings=[], blockers=[], priorities=[])
        top_task = (context.priorities or context.tasks or ["Clarify today's top objective"])[0]
        blockers = ", ".join(context.blockers[:2]) if context.blockers else "No blocker captured"
        audit = WorkflowAuditBlock(
            conclusion=f"Planner prioritized '{top_task}' for immediate execution.",
            evidence=f"Input contained {len(context.tasks)} tasks, {len(context.meetings)} meetings, blockers: {blockers}.",
            risk=f"Planning risk is schedule drift when blockers stay unresolved: {blockers}.",
            next_action="Execute the first priority in a 90-minute focus block and re-evaluate blockers.",
        )
        return audit, "success", ""

    if agent_type == "analyzer":
        technical = payload.technical_input
        if technical is None or (
            not technical.issue_description.strip()
            and not technical.logs.strip()
            and not any(item.strip() for item in technical.errors)
            and not any(item.strip() for item in technical.code_snippets)
        ):
            audit = WorkflowAuditBlock(
                conclusion="Analyzer could not validate a concrete technical issue from the provided context.",
                evidence="No technical issue_description/logs/errors/code snippets were supplied.",
                risk="Skipping validation can hide production regressions and increase time-to-recovery.",
                next_action="Collect one failing log line plus expected-vs-actual behavior, then rerun analyzer step.",
            )
            return audit, "failed", "Gather one concrete error signal and rerun analyzer."

        issue = technical.issue_description.strip() or (technical.errors[0] if technical.errors else "Unknown issue")
        top_error = technical.errors[0] if technical.errors else "No explicit error string supplied."
        audit = WorkflowAuditBlock(
            conclusion=f"Analyzer mapped the issue to a likely root cause cluster around '{issue[:120]}'.",
            evidence=f"Top error signal: {top_error}. Logs length={len(technical.logs.strip())} characters.",
            risk="Applying fixes without validation may create rollback churn in CI/CD environments.",
            next_action="Run one validation step against the highest-probability root cause before applying fixes.",
        )
        return audit, "success", ""

    reflection = payload.reflection_input or DailyReflectionInput(
        completed=[],
        unfinished=[],
        blockers=[],
        mood_or_notes="",
    )
    unfinished = reflection.unfinished[0] if reflection.unfinished else "No unfinished item recorded"
    upstream = previous_audits[-1].conclusion if previous_audits else "No upstream signal"
    audit = WorkflowAuditBlock(
        conclusion=f"Reviewer summarized operational momentum with focus on unfinished item: '{unfinished}'.",
        evidence=f"Completed={len(reflection.completed)}, unfinished={len(reflection.unfinished)}, upstream='{upstream[:120]}'.",
        risk="Reflection quality drops when unfinished items are not converted into tomorrow actions.",
        next_action="Carry one unfinished item into tomorrow's first execution block with a measurable success check.",
    )
    return audit, "success", ""


def _compose_summary(audits: list[WorkflowAuditBlock]) -> WorkflowOrchestrationSummary:
    conclusion = audits[-1].conclusion if audits else "No workflow step executed."
    risks = [audit.risk for audit in audits]
    next_actions = [audit.next_action for audit in audits]
    return WorkflowOrchestrationSummary(conclusion=conclusion, risks=risks, next_actions=next_actions)


def _persist_reusable_assets(
    db: Session,
    record: WorkflowOrchestration,
    summary: WorkflowOrchestrationSummary,
    payload: WorkflowOrchestrationRunRequest,
) -> None:
    if payload.persist_knowledge:
        note = NoteEntry(
            title=f"Workflow Orchestration #{record.id}",
            content=json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            tags_json=json.dumps(["orchestration", record.status, record.subscription_tier]),
        )
        db.add(note)

    if payload.persist_template:
        reusable_template = PromptTemplate(
            name=f"Orchestration Replay #{record.id}",
            description="Auto-generated from orchestration result for reusable follow-up prompts.",
            body=(
                "Use this structured orchestration summary to continue execution.\n\n"
                f"Conclusion: {summary.conclusion}\n"
                f"Risks: {'; '.join(summary.risks[:3])}\n"
                f"Next actions: {'; '.join(summary.next_actions[:3])}"
            ),
            tags_json=json.dumps(["orchestration", "replay", record.subscription_tier]),
        )
        db.add(reusable_template)

    db.commit()


def _to_orchestration_read(
    record: WorkflowOrchestration,
    step_records: list[WorkflowStepRun],
    summary: WorkflowOrchestrationSummary,
    *,
    ledger_integrity: HistoryIntegritySummary | None = None,
    checkpoint_count: int = 0,
) -> WorkflowOrchestrationRead:
    steps = [
        WorkflowStepRunRead(
            id=step.id,
            step_name=step.step_name,
            agent_type=step.agent_type,  # type: ignore[arg-type]
            status=step.status,  # type: ignore[arg-type]
            input_summary=step.input_summary,
            output_summary=step.output_summary,
            audit=WorkflowAuditBlock.model_validate(json.loads(step.audit_json or "{}")),
            fallback_action=step.fallback_action,
            started_at=step.started_at,
            finished_at=step.finished_at,
            duration_ms=step.duration_ms,
        )
        for step in step_records
    ]
    return WorkflowOrchestrationRead(
        id=record.id,
        status=record.status,  # type: ignore[arg-type]
        duration_ms=record.duration_ms,
        entry_source=record.entry_source,
        subscription_tier=normalize_tier(record.subscription_tier),
        team_subject=record.team_subject,
        requested_by=record.requested_by,
        approval_actor=record.approval_actor,
        approval_note=record.approval_note,
        summary=summary,
        steps=steps,
        ledger_integrity=ledger_integrity,
        checkpoint_count=checkpoint_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _trust_metadata_from_payload(payload: WorkflowOrchestrationRunRequest) -> dict[str, str]:
    return {
        "team_subject": _bounded_text(payload.team_subject, fallback="demo-team", limit=120),
        "requested_by": _bounded_text(payload.requested_by, fallback="sre-lead", limit=120),
        "approval_actor": _bounded_text(payload.approval_actor, fallback="", limit=120),
        "approval_note": _bounded_text(payload.approval_note, fallback="", limit=1000),
    }


def _bounded_text(value: str | None, *, fallback: str, limit: int) -> str:
    if value is None:
        return fallback
    clean = value.strip()
    if not clean:
        return fallback
    return clean[:limit]


def _safe_orchestration_summary(record: WorkflowOrchestration) -> WorkflowOrchestrationSummary:
    try:
        return WorkflowOrchestrationSummary.model_validate(json.loads(record.result_json or "{}"))
    except Exception:  # noqa: BLE001
        return WorkflowOrchestrationSummary(
            conclusion=f"Orchestration #{record.id} is {record.status}.",
            risks=[],
            next_actions=[],
        )


def _to_template_read(record: WorkflowTemplate) -> WorkflowTemplateRead:
    steps = [WorkflowStepDefinition.model_validate(item) for item in json.loads(record.steps_json or "[]")]
    tags = _normalize_tags(json.loads(record.tags_json or "[]"))
    return WorkflowTemplateRead(
        id=record.id,
        name=record.name,
        description=record.description,
        steps=steps,
        tags=tags,
        policy=_template_policy_from_tags(tags, steps),
        enabled=record.enabled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        clean = tag.strip().lower()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _write_monetization_event(
    db: Session,
    *,
    event_name: str,
    status: str,
    payload: dict[str, object],
    outcome: str,
) -> None:
    log = log_agent_action(
        db,
        task_type=event_name,
        input_summary=json.dumps(payload, separators=(",", ":"), ensure_ascii=True),
        output_summary=outcome,
        status=status,
    )
    append_monetization_event(
        db,
        log,
        event_name=event_name,
        status=status,
        payload=payload,
        outcome=outcome,
    )
    if event_name == "monetization.usage_recorded":
        endpoint = str(payload.get("endpoint", ""))
        metric = usage_metric_for_endpoint(endpoint)
        billing_subject = payload.get("billing_subject")
        record_plan_usage(
            db,
            subject=billing_subject if isinstance(billing_subject, str) else None,
            metric=metric,
            endpoint=endpoint,
            tier=str(payload.get("tier", "")),
            subject_id=str(payload.get("subject_id", "unknown")),
        )


def _monetization_error(
    *,
    code: str,
    status_code: int,
    message: str,
    **extra: object,
) -> HTTPException:
    detail: dict[str, object] = {
        "code": code,
        "message": message,
    }
    detail.update(extra)
    if code == "upgrade_required" and detail.get("capability") == "multi_step_workflow":
        detail["single-step workflow"] = message
    return HTTPException(status_code=status_code, detail=detail)


def _count_usage_events(db: Session, *, endpoint: str, subject_id: str, window_days: int) -> int:
    window_start = _utcnow() - timedelta(days=max(1, window_days))
    endpoint_needle = _json_field_needle("endpoint", endpoint)
    subject_needle = _json_field_needle("subject_id", subject_id)
    try:
        return int(
            db.query(AgentRunLog)
            .filter(
                AgentRunLog.task_type == "monetization.usage_recorded",
                AgentRunLog.created_at >= window_start,
                AgentRunLog.input_summary.contains(endpoint_needle),
                AgentRunLog.input_summary.contains(subject_needle),
            )
            .count()
        )
    except SQLAlchemyError:
        return 0


def _json_field_needle(key: str, value: str) -> str:
    encoded = json.dumps({key: value}, separators=(",", ":"), ensure_ascii=True)
    return encoded[1:-1]


def _safe_json_dict(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value)
    except Exception:  # noqa: BLE001
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    if len(values) < 2:
        return max(0, values[0])
    percentiles = quantiles(values, n=100, method="inclusive")
    return max(0, int(percentiles[94]))
