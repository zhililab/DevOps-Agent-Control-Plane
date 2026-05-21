import json
import logging

from sqlalchemy.orm import Session

from app.models import DailyPlan
from app.schemas import (
    DailyContextInput,
    DailyPlanHistoryResponse,
    DailyPlanSavedResponse,
    DailyPlanStructured,
)
from app.services.agent_log_service import log_agent_action
from app.services.record_source import SYSTEM_RECORD_SOURCES
from app.time_utils import business_date_from_utc, get_business_timezone_name, utcnow_naive

logger = logging.getLogger(__name__)


def create_daily_plan(db: Session, context: DailyContextInput, *, record_source: str = "user") -> DailyPlanSavedResponse:
    logger.info(
        "daily_plan.request_received tasks=%s meetings=%s blockers=%s priorities=%s",
        len(context.tasks),
        len(context.meetings),
        len(context.blockers),
        len(context.priorities),
    )
    log_agent_action(
        db,
        task_type="daily_plan_request",
        input_summary=json.dumps(context.model_dump(mode="json")),
        output_summary="request accepted",
        status="received",
    )

    generated = _generate_structured_plan(context)
    created_at = utcnow_naive()
    record = DailyPlan(
        plan_date=business_date_from_utc(created_at),
        context_json=json.dumps(context.model_dump(mode="json")),
        output_json=json.dumps(generated.model_dump(mode="json")),
        record_source=record_source,
        business_timezone=get_business_timezone_name(),
        created_at=created_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("daily_plan.persisted plan_id=%s", record.id)
    log_agent_action(
        db,
        task_type="daily_plan_persisted",
        input_summary=f"plan_id={record.id}",
        output_summary=generated.status_summary,
        status="success",
    )

    return DailyPlanSavedResponse(
        id=record.id,
        plan_date=record.plan_date,
        context=context,
        plan=generated,
        created_at=record.created_at,
        record_source=record.record_source,
        business_timezone=record.business_timezone,
    )


def list_daily_plans(db: Session, *, include_system: bool = False) -> DailyPlanHistoryResponse:
    query = db.query(DailyPlan)
    if not include_system:
        query = query.filter(~DailyPlan.record_source.in_(SYSTEM_RECORD_SOURCES))
    records = query.order_by(DailyPlan.created_at.desc(), DailyPlan.id.desc()).all()
    logger.info("daily_plan.history_requested total=%s", len(records))
    items = [
        DailyPlanSavedResponse(
            id=record.id,
            plan_date=record.plan_date,
            context=DailyContextInput.model_validate(json.loads(record.context_json or "{}")),
            plan=DailyPlanStructured.model_validate(json.loads(record.output_json or "{}")),
            created_at=record.created_at,
            record_source=record.record_source,
            business_timezone=record.business_timezone,
        )
        for record in records
    ]
    return DailyPlanHistoryResponse(items=items)


def _generate_structured_plan(context: DailyContextInput) -> DailyPlanStructured:
    priorities = _normalize_lines(context.priorities)
    tasks = _normalize_lines(context.tasks)
    meetings = _normalize_lines(context.meetings)
    blockers = _normalize_lines(context.blockers)

    top_priorities = (priorities or tasks)[:3]
    if not top_priorities:
        top_priorities = ["Clarify one meaningful outcome for today"]

    recommended_order: list[str] = []
    recommended_order.extend(top_priorities)
    recommended_order.extend(item for item in tasks if item not in recommended_order)
    recommended_order.extend(
        f"Prepare for meeting: {meeting}" for meeting in meetings if f"Prepare for meeting: {meeting}" not in recommended_order
    )
    if not tasks and not meetings:
        for default_step in [
            "Define top priority",
            "Plan one focused work block",
            "Review end-of-day status",
        ]:
            if default_step not in recommended_order:
                recommended_order.append(default_step)

    risks = [f"Blocker risk: {blocker}" for blocker in blockers]
    reminders = [f"Reminder: arrive prepared for '{meeting}'" for meeting in meetings]
    risks_and_reminders = (risks + reminders)[:5]
    if not risks_and_reminders:
        risks_and_reminders = ["No major risks captured. Keep monitoring for hidden blockers."]

    next_actions = []
    if recommended_order:
        next_actions.append(f"Start with: {recommended_order[0]}")
    if blockers:
        next_actions.append("Resolve or escalate the highest-impact blocker before noon.")
    if meetings:
        next_actions.append("Draft concise meeting updates before each session.")
    if len(next_actions) < 3:
        next_actions.append("Review progress at end of day and capture carry-over tasks.")
    if len(next_actions) < 3:
        next_actions.append("Prepare tomorrow's first task before ending the day.")

    status_summary = (
        f"Planned {len(tasks)} task(s), {len(meetings)} meeting(s), and {len(blockers)} blocker(s). "
        f"Primary focus: {top_priorities[0] if top_priorities else 'clarify top priority'}"
    )

    return DailyPlanStructured(
        top_priorities=top_priorities,
        recommended_order=recommended_order,
        risks_and_reminders=risks_and_reminders,
        next_actions=next_actions,
        status_summary=status_summary,
    )


def _normalize_lines(items: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized
