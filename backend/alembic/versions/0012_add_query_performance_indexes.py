"""add query performance indexes

Revision ID: 0012_add_query_performance_indexes
Revises: 0011_add_business_time_metadata
Create Date: 2026-05-22 08:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_add_query_performance_indexes"
down_revision = "0011_add_business_time_metadata"
branch_labels = None
depends_on = None


INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    (
        "ix_workflow_orchestrations_created_id",
        "workflow_orchestrations",
        ["created_at", "id"],
    ),
    (
        "ix_workflow_orchestrations_status_created_id",
        "workflow_orchestrations",
        ["status", "created_at", "id"],
    ),
    (
        "ix_workflow_orchestrations_tier_created_id",
        "workflow_orchestrations",
        ["subscription_tier", "created_at", "id"],
    ),
    (
        "ix_workflow_orchestrations_status_tier_created_id",
        "workflow_orchestrations",
        ["status", "subscription_tier", "created_at", "id"],
    ),
    (
        "ix_workflow_step_runs_orchestration_id_id",
        "workflow_step_runs",
        ["orchestration_id", "id"],
    ),
    (
        "ix_workflow_queue_jobs_updated_id",
        "workflow_queue_jobs",
        ["updated_at", "id"],
    ),
    (
        "ix_workflow_queue_jobs_status_updated_id",
        "workflow_queue_jobs",
        ["status", "updated_at", "id"],
    ),
    (
        "ix_workflow_queue_events_job_created_id",
        "workflow_queue_events",
        ["queue_job_id", "created_at", "id"],
    ),
    (
        "ix_agent_run_logs_task_created_id",
        "agent_run_logs",
        ["task_type", "created_at", "id"],
    ),
    (
        "ix_history_events_entity_occurrence",
        "history_events",
        ["entity_type", "entity_id", "occurred_at", "id"],
    ),
    (
        "ix_history_events_correlation_occurrence",
        "history_events",
        ["correlation_id", "occurred_at", "id"],
    ),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, columns in INDEXES:
        _create_index_once(inspector, index_name, table_name, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, _columns in reversed(INDEXES):
        existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)


def _create_index_once(
    inspector: sa.Inspector,
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns)
