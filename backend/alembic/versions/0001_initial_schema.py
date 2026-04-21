"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


task_status = sa.Enum("pending", "in_progress", "done", name="taskstatus")


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("preferences_json", sa.Text(), nullable=False),
        sa.Column("goals_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])

    op.create_table(
        "reflection_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("patterns", sa.Text(), nullable=False),
        sa.Column("next_actions", sa.Text(), nullable=False),
        sa.Column("mood", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reflection_entries_id", "reflection_entries", ["id"])

    op.create_table(
        "agent_run_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_run_logs_id", "agent_run_logs", ["id"])
    op.create_index("ix_agent_run_logs_task_type", "agent_run_logs", ["task_type"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_logs_task_type", table_name="agent_run_logs")
    op.drop_index("ix_agent_run_logs_id", table_name="agent_run_logs")
    op.drop_table("agent_run_logs")

    op.drop_index("ix_reflection_entries_id", table_name="reflection_entries")
    op.drop_table("reflection_entries")

    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_user_profiles_id", table_name="user_profiles")
    op.drop_table("user_profiles")
