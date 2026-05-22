import logging
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.database import engine
from app.db_bootstrap import CORE_TABLES, ensure_core_tables
from app.services.history_ledger import backfill_history_events
from app.services.monetization_service import backfill_current_period_usage_counters

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    return Config(str(backend_dir / "alembic.ini"))


def alembic_version_has_revision(connection: Connection, table_names: set[str] | None = None) -> bool:
    names = table_names if table_names is not None else set(inspect(connection).get_table_names())
    if "alembic_version" not in names:
        return False

    row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
    return bool(row and row[0])


def has_existing_core_schema(connection: Connection, table_names: set[str] | None = None) -> bool:
    names = table_names if table_names is not None else set(inspect(connection).get_table_names())
    return bool(names.intersection(CORE_TABLES))


def should_stamp_existing_schema(connection: Connection) -> bool:
    table_names = set(inspect(connection).get_table_names())
    return has_existing_core_schema(connection, table_names) and not alembic_version_has_revision(
        connection,
        table_names,
    )


def get_current_head(config: Config) -> str:
    head = ScriptDirectory.from_config(config).get_current_head()
    if not head:
        raise RuntimeError("Alembic head revision could not be determined")
    return head


def stamp_existing_schema_at_head(config: Config) -> str:
    head = get_current_head(config)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(128) NOT NULL PRIMARY KEY
                )
                """
            )
        )
        if connection.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))

        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"), {"version_num": head})
    return head


def run_startup_migrations() -> None:
    config = get_alembic_config()

    with engine.connect() as connection:
        stamp_existing_schema = should_stamp_existing_schema(connection)

    if stamp_existing_schema:
        logger.warning(
            "db_migration.existing_schema_without_alembic_revision detected; stamping current schema at head"
        )
        stamped_revision = stamp_existing_schema_at_head(config)
        logger.warning("db_migration.stamped_existing_schema revision=%s", stamped_revision)

    from alembic import command
    command.upgrade(config, "head")
    ensure_core_tables()
    backfill_history_events()
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        backfill_current_period_usage_counters(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_startup_migrations()
