import json

from sqlalchemy.orm import Session

from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskRead, TaskUpdate


VALID_TASK_STATUS = {status.value for status in TaskStatus}


def create_task(db: Session, payload: TaskCreate) -> TaskRead:
    task = Task(
        title=payload.title,
        domain=payload.domain,
        status=TaskStatus(payload.status) if payload.status in VALID_TASK_STATUS else TaskStatus.pending,
        priority=payload.priority,
        source=payload.source,
        context_json=json.dumps(payload.context),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _to_read_model(task)


def list_tasks(db: Session) -> list[TaskRead]:
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return [_to_read_model(task) for task in tasks]


def update_task(db: Session, task_id: int, payload: TaskUpdate) -> TaskRead | None:
    task = db.get(Task, task_id)
    if task is None:
        return None

    if payload.title is not None:
        task.title = payload.title
    if payload.domain is not None:
        task.domain = payload.domain
    if payload.status is not None and payload.status in VALID_TASK_STATUS:
        task.status = TaskStatus(payload.status)
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.source is not None:
        task.source = payload.source
    if payload.context is not None:
        task.context_json = json.dumps(payload.context)

    db.add(task)
    db.commit()
    db.refresh(task)
    return _to_read_model(task)


def _to_read_model(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        title=task.title,
        domain=task.domain,
        status=task.status.value,
        priority=task.priority,
        source=task.source,
        context=json.loads(task.context_json or "{}"),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
