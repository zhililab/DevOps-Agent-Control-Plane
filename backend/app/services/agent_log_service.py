import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AgentRunLog
from app.services.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


def log_agent_action(
    db: Session,
    *,
    task_type: str,
    input_summary: str,
    output_summary: str,
    status: str = "success",
) -> AgentRunLog:
    sanitized = {
        "task_type": sanitize_for_log(task_type, max_chars=64),
        "input_summary": sanitize_for_log(input_summary),
        "output_summary": sanitize_for_log(output_summary),
        "status": sanitize_for_log(status, max_chars=32) or "success",
    }
    log = AgentRunLog(**sanitized)
    db.add(log)

    try:
        db.commit()
        db.refresh(log)
        return log
    except SQLAlchemyError as exc:
        db.rollback()
        message = str(exc).lower()
        missing_table = "agent_run_logs" in message and (
            "does not exist" in message or "no such table" in message
        )
        if not missing_table:
            raise

        logger.warning("agent_log table missing; creating table and retrying once")
        AgentRunLog.__table__.create(bind=db.get_bind(), checkfirst=True)
        retry_log = AgentRunLog(**sanitized)
        db.add(retry_log)
        db.commit()
        db.refresh(retry_log)
        return retry_log
