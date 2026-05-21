import logging

from sqlalchemy import inspect

from app.database import Base, engine
import app.models  # noqa: F401

logger = logging.getLogger(__name__)

CORE_TABLES = (
    "user_profiles",
    "tasks",
    "reflection_entries",
    "agent_run_logs",
    "daily_plans",
    "technical_analyses",
    "note_entries",
    "prompt_templates",
    "workflow_orchestrations",
    "workflow_step_runs",
    "workflow_templates",
    "workflow_queue_jobs",
    "workflow_queue_events",
    "subscription_profiles",
    "usage_counters",
    "monetization_events",
    "history_events",
)


def ensure_core_tables() -> None:
    inspector = inspect(engine)
    missing = [name for name in CORE_TABLES if not inspector.has_table(name)]
    if not missing:
        logger.info("db_bootstrap.core_tables_ok total=%s", len(CORE_TABLES))
        return

    logger.warning("db_bootstrap.missing_tables detected=%s; creating missing tables", ",".join(missing))
    Base.metadata.create_all(bind=engine, checkfirst=True)

    inspector = inspect(engine)
    still_missing = [name for name in CORE_TABLES if not inspector.has_table(name)]
    if still_missing:
        raise RuntimeError(f"Failed to create required tables: {', '.join(still_missing)}")

    logger.info("db_bootstrap.tables_created count=%s", len(missing))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_core_tables()
