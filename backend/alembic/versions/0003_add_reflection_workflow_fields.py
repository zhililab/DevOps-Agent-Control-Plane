"""add reflection workflow fields

Revision ID: 0003_add_reflection_workflow_fields
Revises: 0002_add_daily_plans
Create Date: 2026-04-16 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_reflection_workflow_fields"
down_revision = "0002_add_daily_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reflection_entries",
        sa.Column("completed_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "reflection_entries",
        sa.Column("unfinished_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "reflection_entries",
        sa.Column("blockers_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "reflection_entries",
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("reflection_entries", "notes")
    op.drop_column("reflection_entries", "blockers_json")
    op.drop_column("reflection_entries", "unfinished_json")
    op.drop_column("reflection_entries", "completed_json")
