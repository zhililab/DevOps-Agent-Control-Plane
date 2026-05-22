import json
import logging
from collections.abc import Callable

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session, load_only

from app.database import SessionLocal
from app.models import WorkflowQueueEvent, WorkflowQueueJob
from app.schemas import (
    QueueJobStatus,
    WorkflowOrchestrationRunRequest,
    WorkflowQueueEventRead,
    WorkflowQueueHistoryResponse,
    WorkflowQueueJobRead,
    WorkflowQueueRunResponse,
)
from app.services.history_ledger import append_queue_event_ledger
from app.services.orchestration_service import run_orchestration

logger = logging.getLogger(__name__)


def enqueue_orchestration_run(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    subscription_tier: str,
    background_tasks: BackgroundTasks,
    monetization_context: dict[str, str | int] | None = None,
) -> WorkflowQueueRunResponse:
    request_body: dict[str, object] = {
        "payload": payload.model_dump(mode="json"),
        "subscription_tier": subscription_tier,
    }
    if monetization_context is not None:
        request_body["monetization_context"] = monetization_context
    job = WorkflowQueueJob(
        status="queued",
        attempts=0,
        max_attempts=3,
        cancel_requested=False,
        request_json=json.dumps(request_body, separators=(",", ":"), ensure_ascii=True),
    )
    db.add(job)
    db.flush()
    _append_queue_event(
        db,
        job_id=job.id,
        event_type="queued",
        status="queued",
        detail="Job accepted and queued for background processing.",
    )
    db.commit()
    db.refresh(job)

    if monetization_context is not None:
        from app.services.orchestration_service import _write_monetization_event

        _write_monetization_event(
            db,
            event_name="monetization.usage_recorded",
            status="success",
            payload={
                "endpoint": str(monetization_context.get("endpoint", "/api/orchestrations/queue/run")),
                "tier": str(monetization_context.get("tier", subscription_tier)),
                "subject_id": str(monetization_context.get("subject_id", "unknown")),
                "queue_job_id": job.id,
            },
            outcome="usage recorded after queue accept",
        )

    background_tasks.add_task(_process_queue_job, job.id)
    return WorkflowQueueRunResponse(job_id=job.id, status=job.status, attempts=job.attempts, max_attempts=job.max_attempts)  # type: ignore[arg-type]


def get_queue_job(db: Session, job_id: int) -> WorkflowQueueJobRead:
    job = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    events = _get_queue_events(db, job.id)
    return _to_queue_read(job, events=events)


def list_queue_jobs(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
) -> WorkflowQueueHistoryResponse:
    safe_limit = max(1, min(limit, 200))
    query = db.query(WorkflowQueueJob).options(
        load_only(
            WorkflowQueueJob.id,
            WorkflowQueueJob.status,
            WorkflowQueueJob.attempts,
            WorkflowQueueJob.max_attempts,
            WorkflowQueueJob.cancel_requested,
            WorkflowQueueJob.orchestration_id,
            WorkflowQueueJob.error_message,
            WorkflowQueueJob.created_at,
            WorkflowQueueJob.updated_at,
        )
    )
    if status is not None:
        query = query.filter(WorkflowQueueJob.status == status)
    jobs = (
        query.order_by(WorkflowQueueJob.updated_at.desc(), WorkflowQueueJob.id.desc())
        .limit(safe_limit)
        .all()
    )
    return WorkflowQueueHistoryResponse(items=[_to_queue_read(job) for job in jobs])


def retry_queue_job(db: Session, job_id: int, background_tasks: BackgroundTasks) -> WorkflowQueueRunResponse:
    job = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    if job.status not in {"failed", "canceled"}:
        raise HTTPException(status_code=409, detail="Only failed or canceled jobs can be retried.")
    if job.attempts >= job.max_attempts:
        raise HTTPException(status_code=409, detail="Retry limit reached for this queue job.")

    job.status = "queued"
    job.cancel_requested = False
    job.error_message = ""
    db.add(job)
    _append_queue_event(
        db,
        job_id=job.id,
        event_type="retry_requested",
        status="queued",
        detail=f"Job queued for retry attempt {job.attempts + 1}/{job.max_attempts}.",
    )
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_process_queue_job, job.id)
    return WorkflowQueueRunResponse(job_id=job.id, status=job.status, attempts=job.attempts, max_attempts=job.max_attempts)  # type: ignore[arg-type]


def cancel_queue_job(db: Session, job_id: int) -> WorkflowQueueJobRead:
    job = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    if job.status == "queued":
        job.status = "canceled"
        job.cancel_requested = True
        _append_queue_event(
            db,
            job_id=job.id,
            event_type="cancel_requested",
            status="canceled",
            detail="Cancel requested before execution started.",
        )
    elif job.status == "running":
        job.cancel_requested = True
        _append_queue_event(
            db,
            job_id=job.id,
            event_type="cancel_requested",
            status="running",
            detail="Cancel requested while job is running.",
        )
    elif job.status in {"succeeded", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail="Queue job already finished.")
    db.add(job)
    db.commit()
    db.refresh(job)
    events = _get_queue_events(db, job.id)
    return _to_queue_read(job, events=events)


def _process_queue_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
        if job is None:
            return
        if job.status != "queued":
            return
        if job.cancel_requested:
            job.status = "canceled"
            db.add(job)
            _append_queue_event(
                db,
                job_id=job.id,
                event_type="canceled",
                status="canceled",
                detail="Canceled before execution start due to existing cancel request.",
            )
            db.commit()
            return

        job.status = "running"
        job.attempts += 1
        db.add(job)
        _append_queue_event(
            db,
            job_id=job.id,
            event_type="started",
            status="running",
            detail=f"Execution started (attempt {job.attempts}/{job.max_attempts}).",
        )
        db.commit()
        db.refresh(job)

        request_data = json.loads(job.request_json or "{}")
        payload = WorkflowOrchestrationRunRequest.model_validate(request_data.get("payload", {}))
        subscription_tier = str(request_data.get("subscription_tier", "pro"))

        def _is_cancel_requested() -> bool:
            current = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
            return bool(current.cancel_requested) if current is not None else True

        monetization_context = request_data.get("monetization_context", {})
        result = run_orchestration(
            db,
            payload,
            subscription_tier=subscription_tier,
            should_cancel=_is_cancel_requested,
            monetization_context=monetization_context if isinstance(monetization_context, dict) else None,
        )
        refreshed = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
        if refreshed is None:
            return
        if refreshed.cancel_requested and refreshed.status != "canceled":
            refreshed.status = "canceled"
            refreshed.error_message = "Cancel requested."
            db.add(refreshed)
            _append_queue_event(
                db,
                job_id=refreshed.id,
                event_type="canceled",
                status="canceled",
                detail="Canceled during execution after cancel request was observed.",
            )
            db.commit()
            return
        refreshed.status = "succeeded"
        refreshed.orchestration_id = result.id
        refreshed.error_message = ""
        db.add(refreshed)
        _append_queue_event(
            db,
            job_id=refreshed.id,
            event_type="succeeded",
            status="succeeded",
            detail=f"Execution completed and linked to orchestration #{result.id}.",
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("queue_job.failed job_id=%s", job_id)
        failed = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
        if failed is not None:
            failed.status = "failed"
            failed.error_message = str(exc)[:1000]
            db.add(failed)
            _append_queue_event(
                db,
                job_id=failed.id,
                event_type="failed",
                status="failed",
                detail=f"Execution failed: {failed.error_message}",
            )
            db.commit()
    finally:
        db.close()


def _to_queue_read(job: WorkflowQueueJob, *, events: list[WorkflowQueueEventRead] | None = None) -> WorkflowQueueJobRead:
    return WorkflowQueueJobRead(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        cancel_requested=job.cancel_requested,
        orchestration_id=job.orchestration_id,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        events=events or [],
    )


def _append_queue_event(
    db: Session,
    *,
    job_id: int,
    event_type: str,
    status: QueueJobStatus,
    detail: str,
) -> None:
    event = WorkflowQueueEvent(
        queue_job_id=job_id,
        event_type=event_type,
        status=status,
        detail=detail,
    )
    db.add(event)
    db.flush()
    append_queue_event_ledger(db, event)


def _get_queue_events(db: Session, job_id: int) -> list[WorkflowQueueEventRead]:
    rows = (
        db.query(WorkflowQueueEvent)
        .filter(WorkflowQueueEvent.queue_job_id == job_id)
        .order_by(WorkflowQueueEvent.created_at.asc(), WorkflowQueueEvent.id.asc())
        .all()
    )
    return [
        WorkflowQueueEventRead(
            id=row.id,
            queue_job_id=row.queue_job_id,
            event_type=row.event_type,
            status=row.status,  # type: ignore[arg-type]
            detail=row.detail,
            created_at=row.created_at,
        )
        for row in rows
    ]
