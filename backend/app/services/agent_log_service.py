from sqlalchemy.orm import Session

from app.models import AgentRunLog
from app.services.security_utils import sanitize_for_log


def log_agent_action(
    db: Session,
    *,
    task_type: str,
    input_summary: str,
    output_summary: str,
    status: str = "success",
) -> AgentRunLog:
    log = AgentRunLog(
        task_type=sanitize_for_log(task_type, max_chars=64),
        input_summary=sanitize_for_log(input_summary),
        output_summary=sanitize_for_log(output_summary),
        status=sanitize_for_log(status, max_chars=32) or "success",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
