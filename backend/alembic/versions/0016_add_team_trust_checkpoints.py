"""add team trust checkpoints

Revision ID: 0016_add_team_trust_checkpoints
Revises: 0015_refresh_workflow_template_policies
Create Date: 2026-05-22 14:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_add_team_trust_checkpoints"
down_revision = "0015_refresh_workflow_template_policies"
branch_labels = None
depends_on = None


TRUST_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("team_subject", sa.Column("team_subject", sa.String(length=120), nullable=False, server_default="")),
    ("requested_by", sa.Column("requested_by", sa.String(length=120), nullable=False, server_default="")),
    ("approval_actor", sa.Column("approval_actor", sa.String(length=120), nullable=False, server_default="")),
    ("approval_note", sa.Column("approval_note", sa.Text(), nullable=False, server_default="")),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _add_trust_columns_once(inspector, "workflow_orchestrations")
    _add_trust_columns_once(inspector, "workflow_queue_jobs")

    if "workflow_checkpoints" not in inspector.get_table_names():
        op.create_table(
            "workflow_checkpoints",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("checkpoint_uid", sa.String(length=64), nullable=False),
            sa.Column("entity_type", sa.String(length=32), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=False),
            sa.Column("orchestration_id", sa.Integer(), nullable=True),
            sa.Column("queue_job_id", sa.Integer(), nullable=True),
            sa.Column("checkpoint_type", sa.String(length=80), nullable=False),
            sa.Column("step_name", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("step_index", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("payload_sha256", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=120), nullable=False, server_default="system"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("checkpoint_uid", name="uq_workflow_checkpoints_checkpoint_uid"),
        )

    inspector = sa.inspect(op.get_bind())
    _create_index_once(inspector, "ix_workflow_orchestrations_team_created_id", "workflow_orchestrations", ["team_subject", "created_at", "id"])
    _create_index_once(inspector, "ix_workflow_queue_jobs_team_updated_id", "workflow_queue_jobs", ["team_subject", "updated_at", "id"])
    _create_index_once(inspector, "ix_workflow_checkpoints_checkpoint_uid", "workflow_checkpoints", ["checkpoint_uid"])
    _create_index_once(inspector, "ix_workflow_checkpoints_entity_type", "workflow_checkpoints", ["entity_type"])
    _create_index_once(inspector, "ix_workflow_checkpoints_entity_id", "workflow_checkpoints", ["entity_id"])
    _create_index_once(inspector, "ix_workflow_checkpoints_orchestration_id", "workflow_checkpoints", ["orchestration_id"])
    _create_index_once(inspector, "ix_workflow_checkpoints_queue_job_id", "workflow_checkpoints", ["queue_job_id"])
    _create_index_once(inspector, "ix_workflow_checkpoints_checkpoint_type", "workflow_checkpoints", ["checkpoint_type"])
    _create_index_once(inspector, "ix_workflow_checkpoints_created_at", "workflow_checkpoints", ["created_at"])
    _create_index_once(
        inspector,
        "ix_workflow_checkpoints_orchestration_created_id",
        "workflow_checkpoints",
        ["orchestration_id", "created_at", "id"],
    )
    _create_index_once(
        inspector,
        "ix_workflow_checkpoints_queue_job_created_id",
        "workflow_checkpoints",
        ["queue_job_id", "created_at", "id"],
    )
    _create_index_once(
        inspector,
        "ix_workflow_checkpoints_entity_created_id",
        "workflow_checkpoints",
        ["entity_type", "entity_id", "created_at", "id"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name in (
        ("ix_workflow_checkpoints_entity_created_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_queue_job_created_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_orchestration_created_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_created_at", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_checkpoint_type", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_queue_job_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_orchestration_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_entity_id", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_entity_type", "workflow_checkpoints"),
        ("ix_workflow_checkpoints_checkpoint_uid", "workflow_checkpoints"),
        ("ix_workflow_queue_jobs_team_updated_id", "workflow_queue_jobs"),
        ("ix_workflow_orchestrations_team_created_id", "workflow_orchestrations"),
    ):
        if table_name in inspector.get_table_names() and index_name in {item["name"] for item in inspector.get_indexes(table_name)}:
            op.drop_index(index_name, table_name=table_name)

    if "workflow_checkpoints" in inspector.get_table_names():
        op.drop_table("workflow_checkpoints")

    inspector = sa.inspect(op.get_bind())
    for table_name in ("workflow_queue_jobs", "workflow_orchestrations"):
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, _column in reversed(TRUST_COLUMNS):
            if column_name in existing_columns:
                op.drop_column(table_name, column_name)


def _add_trust_columns_once(inspector: sa.Inspector, table_name: str) -> None:
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, column in TRUST_COLUMNS:
        if column_name not in existing_columns:
            op.add_column(table_name, column.copy())


def _create_index_once(
    inspector: sa.Inspector,
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns)
