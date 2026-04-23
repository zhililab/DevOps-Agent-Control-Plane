import json
import logging
from collections.abc import Callable

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WorkflowQueueJob
from app.schemas import WorkflowOrchestrationRunRequest, WorkflowQueueJobRead, WorkflowQueueRunResponse
from app.services.orchestration_service import run_orchestration

logger = logging.getLogger(__name__)


def enqueue_orchestration_run(
    db: Session,
    payload: WorkflowOrchestrationRunRequest,
    *,
    subscription_tier: str,
    background_tasks: BackgroundTasks,
) -> WorkflowQueueRunResponse:
    job = WorkflowQueueJob(
        status="queued",
        attempts=0,
        max_attempts=3,
        cancel_requested=False,
        request_json=json.dumps(
            {
                "payload": payload.model_dump(mode="json"),
                "subscription_tier": subscription_tier,
            }
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_queue_job, job.id)
    return WorkflowQueueRunResponse(job_id=job.id, status=job.status, attempts=job.attempts, max_attempts=job.max_attempts)  # type: ignore[arg-type]


def get_queue_job(db: Session, job_id: int) -> WorkflowQueueJobRead:
    job = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    return _to_queue_read(job)


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
    elif job.status == "running":
        job.cancel_requested = True
    elif job.status in {"succeeded", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail="Queue job already finished.")
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_queue_read(job)


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
            db.commit()
            return

        job.status = "running"
        job.attempts += 1
        db.add(job)
        db.commit()
        db.refresh(job)

        request_data = json.loads(job.request_json or "{}")
        payload = WorkflowOrchestrationRunRequest.model_validate(request_data.get("payload", {}))
        subscription_tier = str(request_data.get("subscription_tier", "pro"))

        def _is_cancel_requested() -> bool:
            current = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
            return bool(current.cancel_requested) if current is not None else True

        result = run_orchestration(
            db,
            payload,
            subscription_tier=subscription_tier,
            should_cancel=_is_cancel_requested,
        )
        refreshed = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
        if refreshed is None:
            return
        if refreshed.cancel_requested and refreshed.status != "canceled":
            refreshed.status = "canceled"
            refreshed.error_message = "Cancel requested."
            db.add(refreshed)
            db.commit()
            return
        refreshed.status = "succeeded"
        refreshed.orchestration_id = result.id
        refreshed.error_message = ""
        db.add(refreshed)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("queue_job.failed job_id=%s", job_id)
        failed = db.query(WorkflowQueueJob).filter(WorkflowQueueJob.id == job_id).first()
        if failed is not None:
            failed.status = "failed"
            failed.error_message = str(exc)[:1000]
            db.add(failed)
            db.commit()
    finally:
        db.close()


def _to_queue_read(job: WorkflowQueueJob) -> WorkflowQueueJobRead:
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
    )
