"""add business time metadata

Revision ID: 0011_add_business_time_metadata
Revises: 0010_add_history_events
Create Date: 2026-05-22 02:00:00.000000
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa


revision = "0011_add_business_time_metadata"
down_revision = "0010_add_history_events"
branch_labels = None
depends_on = None

BUSINESS_TIMEZONE = "Asia/Shanghai"
SYSTEM_SOURCE = "smoke_check"
USER_SOURCE = "user"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_metadata_columns(inspector, "daily_plans")
    _ensure_metadata_columns(inspector, "reflection_entries")
    _ensure_metadata_columns(inspector, "technical_analyses")

    _backfill_daily_plans(bind)
    _backfill_reflections(bind)
    _backfill_technical_analyses(bind)


def downgrade() -> None:
    for table_name in ("technical_analyses", "reflection_entries", "daily_plans"):
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_columns = _column_names(inspector, table_name)
        existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
        index_name = f"ix_{table_name}_record_source"
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)
        if "business_timezone" in existing_columns:
            op.drop_column(table_name, "business_timezone")
        if "record_source" in existing_columns:
            op.drop_column(table_name, "record_source")


def _ensure_metadata_columns(inspector: sa.Inspector, table_name: str) -> None:
    existing_columns = _column_names(inspector, table_name)
    if "record_source" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column("record_source", sa.String(length=64), nullable=False, server_default=USER_SOURCE),
        )
    if "business_timezone" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column("business_timezone", sa.String(length=64), nullable=False, server_default=BUSINESS_TIMEZONE),
        )

    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    index_name = f"ix_{table_name}_record_source"
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, ["record_source"])


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table_name)}


def _backfill_daily_plans(bind: sa.Connection) -> None:
    rows = bind.execute(sa.text("SELECT id, created_at, context_json FROM daily_plans")).mappings().all()
    for row in rows:
        context = _load_json(row["context_json"])
        bind.execute(
            sa.text(
                "UPDATE daily_plans "
                "SET plan_date = :business_date, record_source = :record_source, business_timezone = :timezone "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "business_date": _business_date(row["created_at"]),
                "record_source": SYSTEM_SOURCE if _is_smoke_daily_plan(context) else USER_SOURCE,
                "timezone": BUSINESS_TIMEZONE,
            },
        )


def _backfill_reflections(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT id, created_at, completed_json, unfinished_json, blockers_json, notes "
            "FROM reflection_entries"
        )
    ).mappings().all()
    for row in rows:
        bind.execute(
            sa.text(
                "UPDATE reflection_entries "
                "SET entry_date = :business_date, record_source = :record_source, business_timezone = :timezone "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "business_date": _business_date(row["created_at"]),
                "record_source": SYSTEM_SOURCE if _is_smoke_reflection(row) else USER_SOURCE,
                "timezone": BUSINESS_TIMEZONE,
            },
        )


def _backfill_technical_analyses(bind: sa.Connection) -> None:
    rows = bind.execute(sa.text("SELECT id, created_at, input_json FROM technical_analyses")).mappings().all()
    for row in rows:
        input_payload = _load_json(row["input_json"])
        bind.execute(
            sa.text(
                "UPDATE technical_analyses "
                "SET analysis_date = :business_date, record_source = :record_source, business_timezone = :timezone "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "business_date": _business_date(row["created_at"]),
                "record_source": SYSTEM_SOURCE if _is_smoke_analysis(input_payload) else USER_SOURCE,
                "timezone": BUSINESS_TIMEZONE,
            },
        )


def _business_date(value: Any) -> date:
    parsed = _parse_datetime(value).astimezone(ZoneInfo(BUSINESS_TIMEZONE))
    return parsed.date()


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_json(value: Any) -> Any:
    try:
        return json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _is_smoke_daily_plan(context: Any) -> bool:
    if not isinstance(context, dict):
        return False
    return (
        context.get("tasks") == ["Smoke task"]
        and context.get("meetings") == ["Smoke meeting"]
        and context.get("blockers") == ["None"]
        and context.get("priorities") == ["Smoke task"]
    )


def _is_smoke_reflection(row: sa.RowMapping) -> bool:
    return (
        _load_json(row["completed_json"]) == ["Done"]
        and _load_json(row["unfinished_json"]) == ["Todo"]
        and _load_json(row["blockers_json"]) == ["Dependency"]
        and str(row["notes"] or "").strip() == "steady"
    )


def _is_smoke_analysis(input_payload: Any) -> bool:
    if not isinstance(input_payload, dict):
        return False
    return (
        input_payload.get("issue_description") == "Smoke issue"
        and input_payload.get("logs") == "error line"
        and input_payload.get("errors") == ["timeout"]
        and input_payload.get("code_snippets") == ["kubectl get pods"]
    )
