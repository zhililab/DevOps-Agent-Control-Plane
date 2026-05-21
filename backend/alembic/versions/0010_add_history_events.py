"""add history events ledger

Revision ID: 0010_add_history_events
Revises: 0009_add_monetization_tables
Create Date: 2026-05-22 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010_add_history_events"
down_revision = "0009_add_monetization_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("history_events"):
        op.create_table(
            "history_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_uid", sa.String(length=128), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("entity_id", sa.String(length=120), nullable=False),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("source_table", sa.String(length=120), nullable=False),
            sa.Column("source_id", sa.String(length=120), nullable=False),
            sa.Column("correlation_id", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("payload_sha256", sa.String(length=64), nullable=False),
            sa.Column("previous_event_sha256", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("occurred_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("integrity_status", sa.String(length=32), nullable=False, server_default="valid"),
            sa.Column("integrity_error", sa.Text(), nullable=False, server_default=""),
            sa.UniqueConstraint("event_uid", name="uq_history_events_event_uid"),
        )

    existing_indexes = {item["name"] for item in inspector.get_indexes("history_events")}
    for index_name, columns in {
        "ix_history_events_id": ["id"],
        "ix_history_events_event_uid": ["event_uid"],
        "ix_history_events_entity_type": ["entity_type"],
        "ix_history_events_entity_id": ["entity_id"],
        "ix_history_events_event_type": ["event_type"],
        "ix_history_events_source_table": ["source_table"],
        "ix_history_events_source_id": ["source_id"],
        "ix_history_events_correlation_id": ["correlation_id"],
        "ix_history_events_occurred_at": ["occurred_at"],
        "ix_history_events_created_at": ["created_at"],
        "ix_history_events_integrity_status": ["integrity_status"],
    }.items():
        if index_name not in existing_indexes:
            op.create_index(index_name, "history_events", columns)


def downgrade() -> None:
    for index_name in (
        "ix_history_events_integrity_status",
        "ix_history_events_created_at",
        "ix_history_events_occurred_at",
        "ix_history_events_correlation_id",
        "ix_history_events_source_id",
        "ix_history_events_source_table",
        "ix_history_events_event_type",
        "ix_history_events_entity_id",
        "ix_history_events_entity_type",
        "ix_history_events_event_uid",
        "ix_history_events_id",
    ):
        op.drop_index(index_name, table_name="history_events")
    op.drop_table("history_events")
