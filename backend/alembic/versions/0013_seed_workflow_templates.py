"""seed workflow templates

Revision ID: 0013_seed_workflow_templates
Revises: 0012_add_query_performance_indexes
Create Date: 2026-05-22 09:20:00.000000
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0013_seed_workflow_templates"
down_revision = "0012_add_query_performance_indexes"
branch_labels = None
depends_on = None

BOOTSTRAP_JSON_PATH = Path(__file__).resolve().parents[2] / "app" / "bootstrap" / "workflow_templates_v1.json"


workflow_templates = sa.table(
    "workflow_templates",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("steps_json", sa.Text),
    sa.column("tags_json", sa.Text),
    sa.column("enabled", sa.Boolean),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for item in _load_templates():
        name = str(item["name"]).strip()
        existing_id = bind.execute(
            sa.select(workflow_templates.c.id).where(workflow_templates.c.name == name)
        ).scalar_one_or_none()
        values = {
            "name": name,
            "description": str(item.get("description", "")).strip(),
            "steps_json": json.dumps(item.get("steps", []), separators=(",", ":"), ensure_ascii=True),
            "tags_json": json.dumps(_normalize_tags(item.get("tags", [])), separators=(",", ":"), ensure_ascii=True),
            "enabled": bool(item.get("enabled", True)),
            "updated_at": now,
        }
        if existing_id is None:
            bind.execute(
                workflow_templates.insert().values(
                    **values,
                    created_at=now,
                )
            )
        else:
            bind.execute(
                workflow_templates.update()
                .where(workflow_templates.c.id == existing_id)
                .values(**values)
            )


def downgrade() -> None:
    names = [str(item["name"]).strip() for item in _load_templates()]
    if names:
        op.get_bind().execute(workflow_templates.delete().where(workflow_templates.c.name.in_(names)))


def _load_templates() -> list[dict[str, Any]]:
    raw = json.loads(BOOTSTRAP_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("Workflow template bootstrap file must contain a list.")
    return [item for item in raw if isinstance(item, dict)]


def _normalize_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        tag = str(item).strip().lower()
        if tag and tag not in normalized:
            normalized.append(tag)
    return normalized
