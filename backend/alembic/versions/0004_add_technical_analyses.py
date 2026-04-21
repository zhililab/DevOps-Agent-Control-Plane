"""add technical analyses table

Revision ID: 0004_add_technical_analyses
Revises: 0003_add_reflection_workflow_fields
Create Date: 2026-04-16 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_technical_analyses"
down_revision = "0003_add_reflection_workflow_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technical_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_technical_analyses_id", "technical_analyses", ["id"])
    op.create_index(
        "ix_technical_analyses_analysis_date",
        "technical_analyses",
        ["analysis_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_technical_analyses_analysis_date", table_name="technical_analyses")
    op.drop_index("ix_technical_analyses_id", table_name="technical_analyses")
    op.drop_table("technical_analyses")
