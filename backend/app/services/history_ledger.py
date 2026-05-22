from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AgentRunLog, HistoryEvent, WorkflowOrchestration, WorkflowQueueEvent, WorkflowQueueJob, WorkflowStepRun
from app.time_utils import as_utc_naive, format_utc_datetime, utcnow_naive

logger = logging.getLogger(__name__)

HISTORY_EVENT_VERSION = 1
SENSITIVE_KEY_PATTERN = re.compile(r"(?i)(authorization|password|passwd|secret|token|api[_-]?key)")
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*([^,\s;\n]+)"),
)


def canonicalize_json(value: Any) -> str:
    return json.dumps(
        _normalize_for_json(_redact_sensitive(value)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def payload_sha256(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def build_event_uid(
    *,
    source_table: str,
    source_id: str | int,
    event_type: str,
    event_version: int = HISTORY_EVENT_VERSION,
) -> str:
    raw = f"{source_table}:{source_id}:{event_type}:{event_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_history_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | int,
    event_type: str,
    source_table: str,
    source_id: str | int,
    payload: dict[str, Any],
    occurred_at: datetime | None = None,
    correlation_id: str | int | None = None,
    event_version: int = HISTORY_EVENT_VERSION,
) -> HistoryEvent:
    source_id_text = str(source_id)
    entity_id_text = str(entity_id)
    event_uid = build_event_uid(
        source_table=source_table,
        source_id=source_id_text,
        event_type=event_type,
        event_version=event_version,
    )
    existing = db.query(HistoryEvent).filter(HistoryEvent.event_uid == event_uid).first()
    if existing is not None:
        return existing

    payload_json = canonicalize_json(payload)
    payload_hash = payload_sha256(payload_json)
    previous = (
        db.query(HistoryEvent)
        .filter(HistoryEvent.entity_type == entity_type, HistoryEvent.entity_id == entity_id_text)
        .order_by(HistoryEvent.occurred_at.desc(), HistoryEvent.id.desc())
        .first()
    )
    event = HistoryEvent(
        event_uid=event_uid,
        entity_type=entity_type,
        entity_id=entity_id_text,
        event_type=event_type,
        event_version=event_version,
        source_table=source_table,
        source_id=source_id_text,
        correlation_id=str(correlation_id or ""),
        payload_json=payload_json,
        payload_sha256=payload_hash,
        previous_event_sha256=previous.payload_sha256 if previous is not None else "",
        occurred_at=_normalize_datetime(occurred_at),
        integrity_status="valid",
        integrity_error="",
    )
    db.add(event)
    try:
        db.commit()
        db.refresh(event)
        return event
    except IntegrityError:
        db.rollback()
        existing = db.query(HistoryEvent).filter(HistoryEvent.event_uid == event_uid).first()
        if existing is not None:
            return existing
        raise


def list_history_events_for_orchestration(db: Session, orchestration_id: int) -> list[HistoryEvent]:
    events = (
        db.query(HistoryEvent)
        .filter(HistoryEvent.entity_type == "orchestration", HistoryEvent.entity_id == str(orchestration_id))
        .all()
    )
    queue_jobs = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.orchestration_id == orchestration_id).all()
    queue_job_ids = [str(job.id) for job in queue_jobs]
    if queue_job_ids:
        events.extend(
            db.query(HistoryEvent)
            .filter(HistoryEvent.entity_type == "queue_job", HistoryEvent.entity_id.in_(queue_job_ids))
            .all()
        )
    return sorted(events, key=lambda event: (event.occurred_at, event.id), reverse=True)


def verify_history_integrity(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | int,
) -> dict[str, Any]:
    events = (
        db.query(HistoryEvent)
        .filter(HistoryEvent.entity_type == entity_type, HistoryEvent.entity_id == str(entity_id))
        .order_by(HistoryEvent.occurred_at.desc(), HistoryEvent.id.desc())
        .all()
    )
    event_results = [_verify_event(event) for event in events]
    status = "valid" if all(item["integrity_status"] == "valid" for item in event_results) else "invalid"
    return {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "integrity_status": status,
        "event_count": len(event_results),
        "events": event_results,
    }


def verify_orchestration_history(db: Session, orchestration_id: int) -> dict[str, Any]:
    events = list_history_events_for_orchestration(db, orchestration_id)
    event_results = [_verify_event(event) for event in events]
    status = "valid" if all(item["integrity_status"] == "valid" for item in event_results) else "invalid"
    return {
        "entity_type": "orchestration",
        "entity_id": str(orchestration_id),
        "integrity_status": status,
        "event_count": len(event_results),
        "events": event_results,
    }


def summarize_orchestration_histories(db: Session, orchestration_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not orchestration_ids:
        return {}

    unique_ids = list(dict.fromkeys(orchestration_ids))
    id_texts = [str(orchestration_id) for orchestration_id in unique_ids]
    events_by_orchestration_id: dict[int, list[HistoryEvent]] = {orchestration_id: [] for orchestration_id in unique_ids}

    orchestration_events = (
        db.query(HistoryEvent)
        .filter(HistoryEvent.entity_type == "orchestration", HistoryEvent.entity_id.in_(id_texts))
        .all()
    )
    for event in orchestration_events:
        try:
            events_by_orchestration_id[int(event.entity_id)].append(event)
        except ValueError:
            continue

    queue_jobs = (
        db.query(WorkflowQueueJob.id, WorkflowQueueJob.orchestration_id)
        .filter(WorkflowQueueJob.orchestration_id.in_(unique_ids))
        .all()
    )
    queue_job_to_orchestration_id = {str(job.id): job.orchestration_id for job in queue_jobs}
    if queue_job_to_orchestration_id:
        queue_events = (
            db.query(HistoryEvent)
            .filter(HistoryEvent.entity_type == "queue_job", HistoryEvent.entity_id.in_(queue_job_to_orchestration_id.keys()))
            .all()
        )
        for event in queue_events:
            orchestration_id = queue_job_to_orchestration_id.get(event.entity_id)
            if orchestration_id is not None:
                events_by_orchestration_id[orchestration_id].append(event)

    summaries: dict[int, dict[str, Any]] = {}
    for orchestration_id, events in events_by_orchestration_id.items():
        ordered_events = sorted(events, key=lambda event: (event.occurred_at, event.id), reverse=True)
        event_results = [_verify_event(event) for event in ordered_events]
        status = "valid" if all(item["integrity_status"] == "valid" for item in event_results) else "invalid"
        summaries[orchestration_id] = {
            "entity_type": "orchestration",
            "entity_id": str(orchestration_id),
            "integrity_status": status,
            "event_count": len(event_results),
        }
    return summaries


def backfill_history_events(db: Session | None = None) -> int:
    owns_session = db is None
    session = db or SessionLocal()
    created = 0
    try:
        created += _backfill_orchestrations(session)
        created += _backfill_steps(session)
        created += _backfill_queue_jobs(session)
        created += _backfill_queue_events(session)
        created += _backfill_agent_logs(session)
        logger.info("history_ledger.backfill_completed created=%s", created)
        return created
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def append_orchestration_accepted_event(db: Session, record: WorkflowOrchestration, request_dump: dict[str, Any]) -> None:
    append_history_event(
        db,
        entity_type="orchestration",
        entity_id=record.id,
        event_type="orchestration.accepted",
        source_table="workflow_orchestrations",
        source_id=record.id,
        correlation_id=record.id,
        occurred_at=record.created_at,
        payload={
            "orchestration_id": record.id,
            "status": record.status,
            "entry_source": record.entry_source,
            "subscription_tier": record.subscription_tier,
            "team_subject": record.team_subject,
            "requested_by": record.requested_by,
            "approval_actor": record.approval_actor,
            "approval_note": record.approval_note,
            "request": request_dump,
        },
    )


def append_orchestration_completed_event(
    db: Session,
    record: WorkflowOrchestration,
    *,
    summary: dict[str, Any],
    step_count: int,
) -> None:
    append_history_event(
        db,
        entity_type="orchestration",
        entity_id=record.id,
        event_type=f"orchestration.{record.status}",
        source_table="workflow_orchestrations",
        source_id=record.id,
        correlation_id=record.id,
        occurred_at=record.updated_at,
        payload={
            "orchestration_id": record.id,
            "status": record.status,
            "duration_ms": record.duration_ms,
            "entry_source": record.entry_source,
            "subscription_tier": record.subscription_tier,
            "team_subject": record.team_subject,
            "requested_by": record.requested_by,
            "approval_actor": record.approval_actor,
            "approval_note": record.approval_note,
            "step_count": step_count,
            "summary": summary,
        },
    )


def append_step_event(db: Session, step: WorkflowStepRun) -> None:
    append_history_event(
        db,
        entity_type="orchestration",
        entity_id=step.orchestration_id,
        event_type=f"step.{step.status}",
        source_table="workflow_step_runs",
        source_id=step.id,
        correlation_id=step.orchestration_id,
        occurred_at=step.finished_at,
        payload={
            "orchestration_id": step.orchestration_id,
            "step_id": step.id,
            "step_name": step.step_name,
            "agent_type": step.agent_type,
            "status": step.status,
            "input": _json_or_raw(step.input_summary),
            "output_summary": step.output_summary,
            "audit": _json_or_raw(step.audit_json),
            "fallback_action": step.fallback_action,
            "started_at": step.started_at,
            "finished_at": step.finished_at,
            "duration_ms": step.duration_ms,
        },
    )


def append_queue_job_event(db: Session, job: WorkflowQueueJob, *, event_type: str, detail: str) -> None:
    append_history_event(
        db,
        entity_type="queue_job",
        entity_id=job.id,
        event_type=f"queue.{event_type}",
        source_table="workflow_queue_jobs",
        source_id=f"{job.id}:{event_type}:{job.status}:{job.attempts}",
        correlation_id=job.orchestration_id or job.id,
        occurred_at=job.updated_at,
        payload={
            "queue_job_id": job.id,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "cancel_requested": job.cancel_requested,
            "orchestration_id": job.orchestration_id,
            "team_subject": job.team_subject,
            "requested_by": job.requested_by,
            "approval_actor": job.approval_actor,
            "approval_note": job.approval_note,
            "request": _json_or_raw(job.request_json),
            "error_message": job.error_message,
            "detail": detail,
        },
    )


def append_queue_event_ledger(db: Session, event: WorkflowQueueEvent) -> None:
    append_history_event(
        db,
        entity_type="queue_job",
        entity_id=event.queue_job_id,
        event_type=f"queue.{event.event_type}",
        source_table="workflow_queue_events",
        source_id=event.id,
        correlation_id=event.queue_job_id,
        occurred_at=event.created_at,
        payload={
            "queue_job_id": event.queue_job_id,
            "queue_event_id": event.id,
            "event_type": event.event_type,
            "status": event.status,
            "detail": event.detail,
        },
    )


def append_monetization_event(
    db: Session,
    log: AgentRunLog,
    *,
    event_name: str,
    status: str,
    payload: dict[str, Any],
    outcome: str,
) -> None:
    subject_id = str(payload.get("subject_id", "unknown"))
    append_history_event(
        db,
        entity_type="monetization",
        entity_id=subject_id,
        event_type=event_name,
        source_table="agent_run_logs",
        source_id=log.id,
        correlation_id=subject_id,
        occurred_at=log.created_at,
        payload={
            "task_type": event_name,
            "status": status,
            "payload": payload,
            "outcome": outcome,
        },
    )


def _verify_event(event: HistoryEvent) -> dict[str, Any]:
    try:
        parsed = json.loads(event.payload_json or "{}")
        canonical = canonicalize_json(parsed)
        actual_hash = payload_sha256(canonical)
        if actual_hash != event.payload_sha256:
            return _event_result(event, "invalid", "payload_sha256 mismatch", payload=parsed if isinstance(parsed, dict) else {})
        return _event_result(event, "valid", "", payload=parsed if isinstance(parsed, dict) else {})
    except Exception as exc:  # noqa: BLE001
        return _event_result(event, "invalid", f"payload_json invalid: {exc}", payload={})


def _event_result(event: HistoryEvent, status: str, error: str, *, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_uid": event.event_uid,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "source_table": event.source_table,
        "source_id": event.source_id,
        "correlation_id": event.correlation_id,
        "payload": payload,
        "payload_sha256": event.payload_sha256,
        "previous_event_sha256": event.previous_event_sha256,
        "occurred_at": event.occurred_at,
        "created_at": event.created_at,
        "integrity_status": status,
        "integrity_error": error,
    }


def _backfill_orchestrations(db: Session) -> int:
    count = 0
    for record in db.query(WorkflowOrchestration).order_by(WorkflowOrchestration.id.asc()).all():
        before = _count_events(db)
        append_history_event(
            db,
            entity_type="orchestration",
            entity_id=record.id,
            event_type="backfilled.orchestration",
            source_table="workflow_orchestrations",
            source_id=record.id,
            correlation_id=record.id,
            occurred_at=record.updated_at,
            payload={
                "orchestration_id": record.id,
                "status": record.status,
                "duration_ms": record.duration_ms,
                "entry_source": record.entry_source,
                "subscription_tier": record.subscription_tier,
                "team_subject": record.team_subject,
                "requested_by": record.requested_by,
                "approval_actor": record.approval_actor,
                "approval_note": record.approval_note,
                "request": _json_or_raw(record.request_json),
                "result": _json_or_raw(record.result_json),
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        count += max(0, _count_events(db) - before)
    return count


def _backfill_steps(db: Session) -> int:
    count = 0
    for step in db.query(WorkflowStepRun).order_by(WorkflowStepRun.id.asc()).all():
        before = _count_events(db)
        append_history_event(
            db,
            entity_type="orchestration",
            entity_id=step.orchestration_id,
            event_type="backfilled.step",
            source_table="workflow_step_runs",
            source_id=step.id,
            correlation_id=step.orchestration_id,
            occurred_at=step.finished_at,
            payload={
                "orchestration_id": step.orchestration_id,
                "step_id": step.id,
                "step_name": step.step_name,
                "agent_type": step.agent_type,
                "status": step.status,
                "input": _json_or_raw(step.input_summary),
                "output_summary": step.output_summary,
                "audit": _json_or_raw(step.audit_json),
                "fallback_action": step.fallback_action,
                "started_at": step.started_at,
                "finished_at": step.finished_at,
                "duration_ms": step.duration_ms,
            },
        )
        count += max(0, _count_events(db) - before)
    return count


def _backfill_queue_jobs(db: Session) -> int:
    count = 0
    for job in db.query(WorkflowQueueJob).order_by(WorkflowQueueJob.id.asc()).all():
        before = _count_events(db)
        append_history_event(
            db,
            entity_type="queue_job",
            entity_id=job.id,
            event_type="backfilled.queue_job",
            source_table="workflow_queue_jobs",
            source_id=job.id,
            correlation_id=job.orchestration_id or job.id,
            occurred_at=job.updated_at,
            payload={
                "queue_job_id": job.id,
                "status": job.status,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "cancel_requested": job.cancel_requested,
                "orchestration_id": job.orchestration_id,
                "team_subject": job.team_subject,
                "requested_by": job.requested_by,
                "approval_actor": job.approval_actor,
                "approval_note": job.approval_note,
                "request": _json_or_raw(job.request_json),
                "error_message": job.error_message,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
        )
        count += max(0, _count_events(db) - before)
    return count


def _backfill_queue_events(db: Session) -> int:
    count = 0
    for event in db.query(WorkflowQueueEvent).order_by(WorkflowQueueEvent.id.asc()).all():
        before = _count_events(db)
        append_history_event(
            db,
            entity_type="queue_job",
            entity_id=event.queue_job_id,
            event_type="backfilled.queue_event",
            source_table="workflow_queue_events",
            source_id=event.id,
            correlation_id=event.queue_job_id,
            occurred_at=event.created_at,
            payload={
                "queue_job_id": event.queue_job_id,
                "queue_event_id": event.id,
                "event_type": event.event_type,
                "status": event.status,
                "detail": event.detail,
            },
        )
        count += max(0, _count_events(db) - before)
    return count


def _backfill_agent_logs(db: Session) -> int:
    count = 0
    rows = (
        db.query(AgentRunLog)
        .filter(AgentRunLog.task_type.like("monetization.%"))
        .filter(~AgentRunLog.task_type.like("%history_requested"))
        .order_by(AgentRunLog.id.asc())
        .all()
    )
    for log in rows:
        before = _count_events(db)
        payload = _json_or_raw(log.input_summary)
        subject_id = payload.get("subject_id", "unknown") if isinstance(payload, dict) else "unknown"
        append_history_event(
            db,
            entity_type="monetization",
            entity_id=str(subject_id),
            event_type="backfilled.agent_log",
            source_table="agent_run_logs",
            source_id=log.id,
            correlation_id=str(subject_id),
            occurred_at=log.created_at,
            payload={
                "agent_run_log_id": log.id,
                "task_type": log.task_type,
                "status": log.status,
                "input": payload,
                "output_summary": log.output_summary,
                "created_at": log.created_at,
            },
        )
        count += max(0, _count_events(db) - before)
    return count


def _count_events(db: Session) -> int:
    return db.query(HistoryEvent).count()


def _json_or_raw(value: str) -> Any:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {"raw": value, "parse_error": "invalid_json"}


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return utcnow_naive()
    return as_utc_naive(value)


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return format_utc_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _normalize_for_json(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_json(item) for item in value]
    return value


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            if SENSITIVE_KEY_PATTERN.search(text_key):
                redacted[text_key] = "<redacted>"
            else:
                redacted[text_key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, str):
        redacted = value
        redacted = SENSITIVE_TEXT_PATTERNS[0].sub("Bearer <redacted>", redacted)
        redacted = SENSITIVE_TEXT_PATTERNS[1].sub(lambda match: f"{match.group(1)}=<redacted>", redacted)
        return redacted
    return value
