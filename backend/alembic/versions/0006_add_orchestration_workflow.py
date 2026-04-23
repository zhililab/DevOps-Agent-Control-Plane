"""add orchestration workflow tables

Revision ID: 0006_add_orchestration_workflow
Revises: 0005_add_knowledge_and_templates
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_add_orchestration_workflow"
down_revision = "0005_add_knowledge_and_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_orchestrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entry_source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("subscription_tier", sa.String(length=16), nullable=False, server_default="pro"),
        sa.Column("request_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workflow_orchestrations_id", "workflow_orchestrations", ["id"])
    op.create_index("ix_workflow_orchestrations_status", "workflow_orchestrations", ["status"])
    op.create_index(
        "ix_workflow_orchestrations_subscription_tier",
        "workflow_orchestrations",
        ["subscription_tier"],
    )

    op.create_table(
        "workflow_step_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("orchestration_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(length=120), nullable=False),
        sa.Column("agent_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("input_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("audit_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("fallback_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workflow_step_runs_id", "workflow_step_runs", ["id"])
    op.create_index("ix_workflow_step_runs_orchestration_id", "workflow_step_runs", ["orchestration_id"])
    op.create_index("ix_workflow_step_runs_agent_type", "workflow_step_runs", ["agent_type"])

    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workflow_templates_id", "workflow_templates", ["id"])
    op.create_index("ix_workflow_templates_name", "workflow_templates", ["name"])


def downgrade() -> None:
    op.drop_index("ix_workflow_templates_name", table_name="workflow_templates")
    op.drop_index("ix_workflow_templates_id", table_name="workflow_templates")
    op.drop_table("workflow_templates")

    op.drop_index("ix_workflow_step_runs_agent_type", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_orchestration_id", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_id", table_name="workflow_step_runs")
    op.drop_table("workflow_step_runs")

    op.drop_index("ix_workflow_orchestrations_subscription_tier", table_name="workflow_orchestrations")
    op.drop_index("ix_workflow_orchestrations_status", table_name="workflow_orchestrations")
    op.drop_index("ix_workflow_orchestrations_id", table_name="workflow_orchestrations")
    op.drop_table("workflow_orchestrations")
