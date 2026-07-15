from alembic import command
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.db_bootstrap import CORE_TABLES
from app.db_migration import (
    alembic_version_has_revision,
    get_alembic_config,
    get_current_head,
    has_existing_core_schema,
    should_stamp_existing_schema,
)
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


def test_startup_migration_stamps_existing_schema_without_version() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE user_profiles (id INTEGER PRIMARY KEY)"))
        assert should_stamp_existing_schema(connection) is True


def test_startup_migration_does_not_stamp_empty_database() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        assert has_existing_core_schema(connection) is False
        assert alembic_version_has_revision(connection) is False
        assert should_stamp_existing_schema(connection) is False


def test_startup_migration_does_not_stamp_when_version_exists() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE user_profiles (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL PRIMARY KEY)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0009_add_monetization_tables')"))

        assert has_existing_core_schema(connection) is True
        assert alembic_version_has_revision(connection) is True
        assert should_stamp_existing_schema(connection) is False


def test_startup_migration_reads_current_alembic_head() -> None:
    assert get_current_head(get_alembic_config()) == "0019_normalize_quality_evidence_subject"


def test_quality_subject_migration_normalizes_legacy_pilot_identity(tmp_path, monkeypatch, request) -> None:
    database_path = tmp_path / "language-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    request.addfinalizer(get_settings.cache_clear)
    config = get_alembic_config()
    command.upgrade(config, "0018_add_llm_evaluation_feedback")

    legacy_subject = "inter" + "view-evidence"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO pilot_measurements (
                    subject, team_subject, metric, phase, value, unit,
                    sample_size, source, notes, measured_at, created_at
                ) VALUES (
                    :subject, 'platform-team', 'release_lead_time_minutes', 'pilot',
                    0.1, 'minutes', 25, 'observed', :notes,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "subject": legacy_subject,
                "notes": f"Legacy {legacy_subject} production observation.",
            },
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT subject, notes FROM pilot_measurements LIMIT 1")
        ).one()
    assert row.subject == "quality-evidence"
    assert row.notes == "Legacy quality-evidence production observation."
