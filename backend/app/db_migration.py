import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.database import engine
from app.db_bootstrap import CORE_TABLES, ensure_core_tables

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


def run_startup_migrations() -> None:
    config = get_alembic_config()

    with engine.connect() as connection:
        stamp_existing_schema = should_stamp_existing_schema(connection)

    if stamp_existing_schema:
        logger.warning(
            "db_migration.existing_schema_without_alembic_revision detected; stamping current schema at head"
        )
        command.stamp(config, "head")

    command.upgrade(config, "head")
    ensure_core_tables()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_startup_migrations()
