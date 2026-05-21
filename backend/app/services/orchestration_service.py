import json
import logging
from datetime import datetime
from datetime import timedelta
from collections.abc import Callable
from statistics import quantiles

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AgentRunLog, NoteEntry, PromptTemplate, WorkflowOrchestration, WorkflowQueueJob, WorkflowStepRun, WorkflowTemplate
from app.schemas import (
    DailyContextInput,
    DailyReflectionInput,
    StepStatus,
    SubscriptionTier,
    TechnicalAnalysisInput,
    WorkflowAuditBlock,
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
)
from app.time_utils import utcnow_naive

logger = logging.getLogger(__name__)

DEFAULT_STEPS = [
    WorkflowStepDefinition(step_name="Plan The Day", agent_type="planner", enabled=True),
    WorkflowStepDefinition(step_name="Analyze Technical Signals", agent_type="analyzer", enabled=True),
    WorkflowStepDefinition(step_name="Review And Reflect", agent_type="reviewer", enabled=True),
]


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
    record = WorkflowOrchestration(
        status="running",
        duration_ms=0,
        entry_source=payload.entry_source.strip() or "manual",
        subscription_tier=tier,
        request_json=json.dumps(request_dump),
        result_json="{}",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    append_orchestration_accepted_event(db, record, request_dump)

    log_agent_action(
        db,
        task_type="workflow_orchestration_request",
        input_summary=json.dumps({"id": record.id, "tier": tier, "steps": len(active_steps)}),
        output_summary="orchestration accepted",
        status="received",
    )

    step_records: list[WorkflowStepRun] = []
    previous_audits: list[WorkflowAuditBlock] = []
    has_failure = False

    for step in active_steps:
        if should_cancel and should_cancel():
            has_failure = True
            step_started = _utcnow()
            step_finished = _utcnow()
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
            step_records.append(step_record)
            previous_audits.append(canceled_audit)
            break

        step_started = _utcnow()
        step_input = _build_step_input(step.agent_type, payload, previous_audits)
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
                "orchestration_id": record.id,
            },
            outcome="usage recorded after workflow execution",
        )
    return _to_orchestration_read(record, step_records, summary)


def enforce_monetization_policy_for_run(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    tier: str,
    subject_id: str,
    endpoint: str,
) -> dict[str, int]:
    normalized_tier = normalize_tier(tier)
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
) -> WorkflowOrchestrationHistoryResponse:
    query = db.query(WorkflowOrchestration)
    if status:
        query = query.filter(WorkflowOrchestration.status == status.strip().lower())
    if subscription_tier:
        query = query.filter(WorkflowOrchestration.subscription_tier == normalize_tier(subscription_tier))
    records = query.order_by(WorkflowOrchestration.created_at.desc()).limit(max(1, min(limit, 200))).all()

    items = []
    for record in records:
        steps = (
            db.query(WorkflowStepRun)
            .filter(WorkflowStepRun.orchestration_id == record.id)
            .order_by(WorkflowStepRun.id.asc())
            .all()
        )
        summary = WorkflowOrchestrationSummary.model_validate(json.loads(record.result_json or "{}"))
        items.append(_to_orchestration_read(record, steps, summary))
    return WorkflowOrchestrationHistoryResponse(items=items)


def get_orchestration_metrics(db: Session, *, days: int = 7) -> WorkflowOrchestrationMetricsResponse:
    period_days = max(1, min(days, 90))
    window_start = _utcnow() - timedelta(days=period_days)
    records = (
        db.query(WorkflowOrchestration)
        .filter(WorkflowOrchestration.created_at >= window_start)
        .order_by(WorkflowOrchestration.created_at.desc())
        .all()
    )
    total_runs = len(records)
    partial_count = len([record for record in records if record.status == "partial_success"])
    duration_total = sum(max(0, record.duration_ms) for record in records)
    average_duration_ms = int(duration_total / total_runs) if total_runs > 0 else 0
    partial_success_rate = round((partial_count / total_runs), 4) if total_runs > 0 else 0.0

    return WorkflowOrchestrationMetricsResponse(
        period_days=period_days,
        total_runs=total_runs,
        weekly_active_orchestrations=total_runs,
        partial_success_rate=partial_success_rate,
        average_duration_ms=average_duration_ms,
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
    summary = WorkflowOrchestrationSummary.model_validate(json.loads(record.result_json or "{}"))
    return _to_orchestration_read(record, steps, summary)


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
    record = WorkflowTemplate(
        name=payload.name.strip(),
        description=payload.description.strip(),
        steps_json=json.dumps([step.model_dump(mode="json") for step in payload.steps]),
        tags_json=json.dumps(_normalize_tags(payload.tags)),
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
    if payload.tags is not None:
        record.tags_json = json.dumps(_normalize_tags(payload.tags))
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
    records = query.order_by(WorkflowTemplate.updated_at.desc()).all()
    return [_to_template_read(record) for record in records]


def export_workflow_templates(db: Session) -> list[WorkflowTemplateRead]:
    return list_workflow_templates(db)


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
            matched.tags_json = json.dumps(_normalize_tags(item.tags))
            matched.enabled = item.enabled
            db.add(matched)
            updated += 1
            continue
        record = WorkflowTemplate(
            name=item.name.strip(),
            description=item.description.strip(),
            steps_json=json.dumps([step.model_dump(mode="json") for step in item.steps]),
            tags_json=json.dumps(_normalize_tags(item.tags)),
            enabled=item.enabled,
        )
        db.add(record)
        imported += 1

    db.commit()
    total = len(payload.items)
    if imported + updated < total:
        skipped = total - imported - updated
    return WorkflowTemplateImportResponse(imported=imported, updated=updated, skipped=skipped, total=total)


def _resolve_steps(db: Session, payload: WorkflowOrchestrationRunRequest) -> list[WorkflowStepDefinition]:
    if payload.template_id is not None:
        template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == payload.template_id).first()
        if template is None:
            raise HTTPException(status_code=404, detail="Workflow template not found.")
        return [WorkflowStepDefinition.model_validate(item) for item in json.loads(template.steps_json or "[]")]
    if payload.steps:
        return payload.steps
    return DEFAULT_STEPS


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
        summary=summary,
        steps=steps,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_template_read(record: WorkflowTemplate) -> WorkflowTemplateRead:
    return WorkflowTemplateRead(
        id=record.id,
        name=record.name,
        description=record.description,
        steps=[WorkflowStepDefinition.model_validate(item) for item in json.loads(record.steps_json or "[]")],
        tags=_normalize_tags(json.loads(record.tags_json or "[]")),
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
    try:
        rows = (
            db.query(AgentRunLog)
            .filter(
                AgentRunLog.task_type == "monetization.usage_recorded",
                AgentRunLog.created_at >= window_start,
            )
            .all()
        )
    except SQLAlchemyError:
        return 0
    count = 0
    for row in rows:
        payload = _safe_json_dict(row.input_summary)
        if payload.get("endpoint") == endpoint and payload.get("subject_id") == subject_id:
            count += 1
    return count


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
