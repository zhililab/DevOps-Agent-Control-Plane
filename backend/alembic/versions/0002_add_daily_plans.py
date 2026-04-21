"""add daily plans table

Revision ID: 0002_add_daily_plans
Revises: 0001_initial_schema
Create Date: 2026-04-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_daily_plans"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_daily_plans_id", "daily_plans", ["id"])
    op.create_index("ix_daily_plans_plan_date", "daily_plans", ["plan_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_plans_plan_date", table_name="daily_plans")
    op.drop_index("ix_daily_plans_id", table_name="daily_plans")
    op.drop_table("daily_plans")
