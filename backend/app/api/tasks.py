from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import create_task, list_tasks, update_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead)
def create_task_endpoint(payload: TaskCreate, db: Session = Depends(get_db)) -> TaskRead:
    return create_task(db, payload)


@router.get("", response_model=list[TaskRead])
def list_tasks_endpoint(db: Session = Depends(get_db)) -> list[TaskRead]:
    return list_tasks(db)


@router.put("/{task_id}", response_model=TaskRead)
def update_task_endpoint(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> TaskRead:
    task = update_task(db, task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
