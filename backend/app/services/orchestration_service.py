import json
import logging
from datetime import datetime, timezone
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import NoteEntry, PromptTemplate, WorkflowOrchestration, WorkflowStepRun, WorkflowTemplate
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

logger = logging.getLogger(__name__)

DEFAULT_STEPS = [
    WorkflowStepDefinition(step_name="Plan The Day", agent_type="planner", enabled=True),
    WorkflowStepDefinition(step_name="Analyze Technical Signals", agent_type="analyzer", enabled=True),
    WorkflowStepDefinition(step_name="Review And Reflect", agent_type="reviewer", enabled=True),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
) -> WorkflowOrchestrationRead:
    tier = normalize_tier(subscription_tier)
    steps = _resolve_steps(db, payload)
    active_steps = [step for step in steps if step.enabled]

    if tier == "free" and len(active_steps) > 1:
        raise HTTPException(status_code=403, detail="Free tier supports a single-step workflow only.")

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

    _persist_reusable_assets(db, record, summary, payload)
    log_agent_action(
        db,
        task_type="workflow_orchestration_completed",
        input_summary=f"orchestration_id={record.id}",
        output_summary=summary.conclusion,
        status=status,
    )
    return _to_orchestration_read(record, step_records, summary)


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
