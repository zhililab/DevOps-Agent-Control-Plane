"""add orchestration queue jobs

Revision ID: 0007_add_orchestration_queue_jobs
Revises: 0006_add_orchestration_workflow
Create Date: 2026-04-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_add_orchestration_queue_jobs"
down_revision = "0006_add_orchestration_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("workflow_queue_jobs"):
        op.create_table(
            "workflow_queue_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("orchestration_id", sa.Integer(), nullable=True),
            sa.Column("request_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    existing_indexes = {item["name"] for item in inspector.get_indexes("workflow_queue_jobs")}
    if "ix_workflow_queue_jobs_id" not in existing_indexes:
        op.create_index("ix_workflow_queue_jobs_id", "workflow_queue_jobs", ["id"])
    if "ix_workflow_queue_jobs_status" not in existing_indexes:
        op.create_index("ix_workflow_queue_jobs_status", "workflow_queue_jobs", ["status"])
    if "ix_workflow_queue_jobs_orchestration_id" not in existing_indexes:
        op.create_index(
            "ix_workflow_queue_jobs_orchestration_id",
            "workflow_queue_jobs",
            ["orchestration_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_workflow_queue_jobs_orchestration_id", table_name="workflow_queue_jobs")
    op.drop_index("ix_workflow_queue_jobs_status", table_name="workflow_queue_jobs")
    op.drop_index("ix_workflow_queue_jobs_id", table_name="workflow_queue_jobs")
    op.drop_table("workflow_queue_jobs")
