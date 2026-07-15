"""normalize customer-facing quality evidence language

Revision ID: 0019_normalize_quality_evidence_subject
Revises: 0018_add_llm_evaluation_feedback
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "0019_normalize_quality_evidence_subject"
down_revision = "0018_add_llm_evaluation_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_replaceable_text(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, sa.String) and not isinstance(column_type, sa.Enum)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    legacy_term = "inter" + "view"
    replacements = (
        (legacy_term, "quality"),
        (legacy_term.title(), "Quality"),
        (legacy_term.upper(), "QUALITY"),
    )

    for table_name in sa.inspect(bind).get_table_names():
        table = sa.Table(table_name, metadata, autoload_with=bind)
        for column in table.columns:
            if not _is_replaceable_text(column.type):
                continue
            for old_value, new_value in replacements:
                bind.execute(
                    table.update()
                    .where(column.contains(old_value))
                    .values({column.name: sa.func.replace(column, old_value, new_value)})
                )


def downgrade() -> None:
    # Product-language normalization is intentionally irreversible.
    pass
