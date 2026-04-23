from sqlalchemy import create_engine, text

from app.db_bootstrap import CORE_TABLES
from app.models import Base


def test_core_tables_list_includes_daily_plan_and_agent_logs() -> None:
    assert "daily_plans" in CORE_TABLES
    assert "agent_run_logs" in CORE_TABLES


def test_create_all_restores_missing_core_tables_for_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS daily_plans"))
        connection.execute(text("DROP TABLE IF EXISTS agent_run_logs"))
    Base.metadata.create_all(bind=engine, checkfirst=True)

    with engine.begin() as connection:
        daily_plans_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_plans'")
        ).fetchone()
        agent_logs_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_run_logs'")
        ).fetchone()

    assert daily_plans_exists is not None
    assert agent_logs_exists is not None
