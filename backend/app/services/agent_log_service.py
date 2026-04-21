from sqlalchemy.orm import Session

from app.models import AgentRunLog


def log_agent_action(
    db: Session,
    *,
    task_type: str,
    input_summary: str,
    output_summary: str,
    status: str = "success",
) -> AgentRunLog:
    log = AgentRunLog(
        task_type=task_type,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
