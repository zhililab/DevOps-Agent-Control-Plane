"""add ai pr release gate template

Revision ID: 0017_add_ai_pr_release_gate_template
Revises: 0016_add_team_trust_checkpoints
Create Date: 2026-05-24 00:00:00.000000
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0017_add_ai_pr_release_gate_template"
down_revision = "0016_add_team_trust_checkpoints"
branch_labels = None
depends_on = None

BOOTSTRAP_JSON_PATH = Path(__file__).resolve().parents[2] / "app" / "bootstrap" / "workflow_templates_v1.json"
TEMPLATE_NAME = "AI-generated PR Release Gate"


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
    item = _load_template()
    existing_id = bind.execute(
        sa.select(workflow_templates.c.id).where(workflow_templates.c.name == TEMPLATE_NAME)
    ).scalar_one_or_none()
    values = {
        "name": TEMPLATE_NAME,
        "description": str(item.get("description", "")).strip(),
        "steps_json": json.dumps(item.get("steps", []), separators=(",", ":"), ensure_ascii=True),
        "tags_json": json.dumps(_normalize_tags(item.get("tags", [])), separators=(",", ":"), ensure_ascii=True),
        "enabled": bool(item.get("enabled", True)),
        "updated_at": now,
    }
    if existing_id is None:
        bind.execute(workflow_templates.insert().values(**values, created_at=now))
    else:
        bind.execute(workflow_templates.update().where(workflow_templates.c.id == existing_id).values(**values))


def downgrade() -> None:
    op.get_bind().execute(workflow_templates.delete().where(workflow_templates.c.name == TEMPLATE_NAME))


def _load_template() -> dict[str, Any]:
    raw = json.loads(BOOTSTRAP_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("Workflow template bootstrap file must contain a list.")
    for item in raw:
        if isinstance(item, dict) and str(item.get("name", "")).strip() == TEMPLATE_NAME:
            return item
    raise RuntimeError(f"Missing builtin workflow template: {TEMPLATE_NAME}")


def _normalize_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        tag = str(item).strip().lower()
        if tag and tag not in normalized:
            normalized.append(tag)
    return normalized
