"""add workflow queue events

Revision ID: 0008_add_workflow_queue_events
Revises: 0007_add_orchestration_queue_jobs
Create Date: 2026-04-24 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008_add_workflow_queue_events"
down_revision = "0007_add_orchestration_queue_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("workflow_queue_events"):
        op.create_table(
            "workflow_queue_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("queue_job_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    existing_indexes = {item["name"] for item in inspector.get_indexes("workflow_queue_events")}
    if "ix_workflow_queue_events_id" not in existing_indexes:
        op.create_index("ix_workflow_queue_events_id", "workflow_queue_events", ["id"])
    if "ix_workflow_queue_events_queue_job_id" not in existing_indexes:
        op.create_index("ix_workflow_queue_events_queue_job_id", "workflow_queue_events", ["queue_job_id"])
    if "ix_workflow_queue_events_event_type" not in existing_indexes:
        op.create_index("ix_workflow_queue_events_event_type", "workflow_queue_events", ["event_type"])
    if "ix_workflow_queue_events_created_at" not in existing_indexes:
        op.create_index("ix_workflow_queue_events_created_at", "workflow_queue_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_queue_events_created_at", table_name="workflow_queue_events")
    op.drop_index("ix_workflow_queue_events_event_type", table_name="workflow_queue_events")
    op.drop_index("ix_workflow_queue_events_queue_job_id", table_name="workflow_queue_events")
    op.drop_index("ix_workflow_queue_events_id", table_name="workflow_queue_events")
    op.drop_table("workflow_queue_events")

