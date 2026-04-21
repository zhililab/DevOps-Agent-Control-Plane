"""add knowledge and templates tables

Revision ID: 0005_add_knowledge_and_templates
Revises: 0004_add_technical_analyses
Create Date: 2026-04-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_knowledge_and_templates"
down_revision = "0004_add_technical_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "note_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_note_entries_id", "note_entries", ["id"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_prompt_templates_id", "prompt_templates", ["id"])


def downgrade() -> None:
    op.drop_index("ix_prompt_templates_id", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    op.drop_index("ix_note_entries_id", table_name="note_entries")
    op.drop_table("note_entries")
