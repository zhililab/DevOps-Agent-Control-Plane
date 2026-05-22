from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import WorkflowCheckpoint, WorkflowOrchestration, WorkflowQueueJob
from app.schemas import WorkflowCheckpointRead
from app.services.history_ledger import canonicalize_json, payload_sha256
from app.time_utils import utcnow_naive


def append_workflow_checkpoint(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | int,
    checkpoint_type: str,
    status: str,
    payload: dict[str, Any],
    orchestration_id: int | None = None,
    queue_job_id: int | None = None,
    step_name: str = "",
    step_index: int | None = None,
    created_by: str = "system",
    occurred_at: datetime | None = None,
    uid_hint: str | int | None = None,
) -> WorkflowCheckpoint:
    normalized_payload = {
        **payload,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "checkpoint_type": checkpoint_type,
        "status": status,
        "orchestration_id": orchestration_id,
        "queue_job_id": queue_job_id,
        "step_name": step_name,
        "step_index": step_index,
        "created_by": _clean_actor(created_by),
    }
    payload_json = canonicalize_json(normalized_payload)
    payload_hash = payload_sha256(payload_json)
    checkpoint_uid = _checkpoint_uid(
        entity_type=entity_type,
        entity_id=entity_id,
        checkpoint_type=checkpoint_type,
        status=status,
        uid_hint=uid_hint or payload_hash,
    )
    existing = db.query(WorkflowCheckpoint).filter(WorkflowCheckpoint.checkpoint_uid == checkpoint_uid).first()
    if existing is not None:
        return existing

    record = WorkflowCheckpoint(
        checkpoint_uid=checkpoint_uid,
        entity_type=entity_type,
        entity_id=str(entity_id),
        orchestration_id=orchestration_id,
        queue_job_id=queue_job_id,
        checkpoint_type=checkpoint_type,
        step_name=step_name,
        step_index=step_index,
        status=status,
        payload_json=payload_json,
        payload_sha256=payload_hash,
        created_by=_clean_actor(created_by),
        created_at=occurred_at or utcnow_naive(),
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        return record
    except IntegrityError:
        db.rollback()
        existing = db.query(WorkflowCheckpoint).filter(WorkflowCheckpoint.checkpoint_uid == checkpoint_uid).first()
        if existing is not None:
            return existing
        raise


def append_orchestration_checkpoint(
    db: Session,
    record: WorkflowOrchestration,
    *,
    checkpoint_type: str,
    payload: dict[str, Any],
    status: str | None = None,
    step_name: str = "",
    step_index: int | None = None,
    created_by: str | None = None,
    occurred_at: datetime | None = None,
    uid_hint: str | int | None = None,
) -> WorkflowCheckpoint:
    return append_workflow_checkpoint(
        db,
        entity_type="orchestration",
        entity_id=record.id,
        checkpoint_type=checkpoint_type,
        status=status or record.status,
        payload={
            "team_subject": record.team_subject,
            "requested_by": record.requested_by,
            "approval_actor": record.approval_actor,
            "approval_note": record.approval_note,
            **payload,
        },
        orchestration_id=record.id,
        step_name=step_name,
        step_index=step_index,
        created_by=created_by or record.requested_by or record.approval_actor or "system",
        occurred_at=occurred_at,
        uid_hint=uid_hint,
    )


def append_queue_checkpoint(
    db: Session,
    job: WorkflowQueueJob,
    *,
    checkpoint_type: str,
    detail: str,
    actor: str | None = None,
    uid_hint: str | int | None = None,
) -> WorkflowCheckpoint:
    return append_workflow_checkpoint(
        db,
        entity_type="queue_job",
        entity_id=job.id,
        checkpoint_type=f"queue.{checkpoint_type}",
        status=job.status,
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
            "detail": detail,
            "request": _json_or_empty(job.request_json),
            "error_message": job.error_message,
        },
        orchestration_id=job.orchestration_id,
        queue_job_id=job.id,
        created_by=actor or job.requested_by or job.approval_actor or "system",
        occurred_at=job.updated_at,
        uid_hint=uid_hint,
    )


def list_checkpoints_for_orchestration(db: Session, orchestration_id: int) -> list[WorkflowCheckpoint]:
    queue_job_ids = [
        item.id
        for item in db.query(WorkflowQueueJob.id)
        .filter(WorkflowQueueJob.orchestration_id == orchestration_id)
        .all()
    ]
    filters = [WorkflowCheckpoint.orchestration_id == orchestration_id]
    if queue_job_ids:
        filters.append(WorkflowCheckpoint.queue_job_id.in_(queue_job_ids))
    return (
        db.query(WorkflowCheckpoint)
        .filter(or_(*filters))
        .order_by(WorkflowCheckpoint.created_at.desc(), WorkflowCheckpoint.id.desc())
        .all()
    )


def list_checkpoints_for_queue_job(db: Session, queue_job_id: int) -> list[WorkflowCheckpoint]:
    return (
        db.query(WorkflowCheckpoint)
        .filter(WorkflowCheckpoint.queue_job_id == queue_job_id)
        .order_by(WorkflowCheckpoint.created_at.asc(), WorkflowCheckpoint.id.asc())
        .all()
    )


def summarize_checkpoint_counts(db: Session, orchestration_ids: list[int]) -> dict[int, int]:
    if not orchestration_ids:
        return {}

    unique_ids = list(dict.fromkeys(orchestration_ids))
    counts: dict[int, int] = {orchestration_id: 0 for orchestration_id in unique_ids}
    orchestration_counts = (
        db.query(WorkflowCheckpoint.orchestration_id, func.count(WorkflowCheckpoint.id))
        .filter(
            WorkflowCheckpoint.orchestration_id.in_(unique_ids),
            WorkflowCheckpoint.queue_job_id.is_(None),
        )
        .group_by(WorkflowCheckpoint.orchestration_id)
        .all()
    )
    for orchestration_id, count in orchestration_counts:
        if orchestration_id is not None:
            counts[int(orchestration_id)] = counts.get(int(orchestration_id), 0) + int(count)

    queue_jobs = (
        db.query(WorkflowQueueJob.id, WorkflowQueueJob.orchestration_id)
        .filter(WorkflowQueueJob.orchestration_id.in_(unique_ids))
        .all()
    )
    queue_job_to_orchestration_id = {job.id: job.orchestration_id for job in queue_jobs}
    if queue_job_to_orchestration_id:
        queue_counts = (
            db.query(WorkflowCheckpoint.queue_job_id, func.count(WorkflowCheckpoint.id))
            .filter(WorkflowCheckpoint.queue_job_id.in_(queue_job_to_orchestration_id.keys()))
            .group_by(WorkflowCheckpoint.queue_job_id)
            .all()
        )
        for queue_job_id, count in queue_counts:
            orchestration_id = queue_job_to_orchestration_id.get(queue_job_id)
            if orchestration_id is not None:
                counts[int(orchestration_id)] = counts.get(int(orchestration_id), 0) + int(count)

    return counts


def verify_checkpoint_payload(record: WorkflowCheckpoint) -> dict[str, Any]:
    try:
        parsed = json.loads(record.payload_json or "{}")
        if not isinstance(parsed, dict):
            parsed = {}
        actual_hash = payload_sha256(canonicalize_json(parsed))
        if actual_hash != record.payload_sha256:
            return {"payload": parsed, "integrity_status": "invalid", "integrity_error": "payload_sha256 mismatch"}
        return {"payload": parsed, "integrity_status": "valid", "integrity_error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"payload": {}, "integrity_status": "invalid", "integrity_error": f"payload_json invalid: {exc}"}


def to_checkpoint_read(record: WorkflowCheckpoint) -> WorkflowCheckpointRead:
    verification = verify_checkpoint_payload(record)
    return WorkflowCheckpointRead(
        id=record.id,
        checkpoint_uid=record.checkpoint_uid,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        orchestration_id=record.orchestration_id,
        queue_job_id=record.queue_job_id,
        checkpoint_type=record.checkpoint_type,
        step_name=record.step_name,
        step_index=record.step_index,
        status=record.status,
        payload=verification["payload"],
        payload_sha256=record.payload_sha256,
        created_by=record.created_by,
        created_at=record.created_at,
        integrity_status=verification["integrity_status"],
        integrity_error=verification["integrity_error"],
    )


def _checkpoint_uid(
    *,
    entity_type: str,
    entity_id: str | int,
    checkpoint_type: str,
    status: str,
    uid_hint: str | int,
) -> str:
    raw = f"{entity_type}:{entity_id}:{checkpoint_type}:{status}:{uid_hint}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clean_actor(value: str) -> str:
    clean = value.strip()
    return clean[:120] if clean else "system"


def _json_or_empty(value: str) -> Any:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
