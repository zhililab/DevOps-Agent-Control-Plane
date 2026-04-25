"""add monetization tables

Revision ID: 0009_add_monetization_tables
Revises: 0008_add_workflow_queue_events
Create Date: 2026-04-24 01:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_add_monetization_tables"
down_revision = "0008_add_workflow_queue_events"
branch_labels = None
depends_on = None


subscription_tier_enum = sa.Enum("free", "pro", "power", name="subscriptiontier", native_enum=False)
subscription_status_enum = sa.Enum(
    "inactive",
    "active",
    "past_due",
    "canceled",
    name="subscriptionstatus",
    native_enum=False,
)
usage_metric_enum = sa.Enum("workflow_runs", "queued_runs", name="usagemetric", native_enum=False)
monetization_event_kind_enum = sa.Enum(
    "subscription_changed",
    "usage_recorded",
    "usage_limit_reached",
    "entitlement_checked",
    name="monetizationeventkind",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("subscription_profiles"):
        op.create_table(
            "subscription_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subject", sa.String(length=120), nullable=False),
            sa.Column("tier", subscription_tier_enum, nullable=False, server_default="free"),
            sa.Column("status", subscription_status_enum, nullable=False, server_default="inactive"),
            sa.Column("billing_provider", sa.String(length=32), nullable=False, server_default="manual"),
            sa.Column("external_customer_id", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("external_subscription_id", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("current_period_start", sa.DateTime(), nullable=True),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column(
                "cancel_at_period_end",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("entitlements_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    existing_subscription_indexes = {item["name"] for item in inspector.get_indexes("subscription_profiles")}
    if "ix_subscription_profiles_id" not in existing_subscription_indexes:
        op.create_index("ix_subscription_profiles_id", "subscription_profiles", ["id"])
    if "ix_subscription_profiles_subject" not in existing_subscription_indexes:
        op.create_index("ix_subscription_profiles_subject", "subscription_profiles", ["subject"])
    if "ix_subscription_profiles_tier" not in existing_subscription_indexes:
        op.create_index("ix_subscription_profiles_tier", "subscription_profiles", ["tier"])
    if "ix_subscription_profiles_status" not in existing_subscription_indexes:
        op.create_index("ix_subscription_profiles_status", "subscription_profiles", ["status"])

    if not inspector.has_table("usage_counters"):
        op.create_table(
            "usage_counters",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subscription_profile_id", sa.Integer(), nullable=False),
            sa.Column("metric", usage_metric_enum, nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("limit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    existing_usage_indexes = {item["name"] for item in inspector.get_indexes("usage_counters")}
    if "ix_usage_counters_id" not in existing_usage_indexes:
        op.create_index("ix_usage_counters_id", "usage_counters", ["id"])
    if "ix_usage_counters_subscription_profile_id" not in existing_usage_indexes:
        op.create_index(
            "ix_usage_counters_subscription_profile_id",
            "usage_counters",
            ["subscription_profile_id"],
        )
    if "ix_usage_counters_metric" not in existing_usage_indexes:
        op.create_index("ix_usage_counters_metric", "usage_counters", ["metric"])
    if "ix_usage_counters_period_start" not in existing_usage_indexes:
        op.create_index("ix_usage_counters_period_start", "usage_counters", ["period_start"])
    if "ix_usage_counters_period_end" not in existing_usage_indexes:
        op.create_index("ix_usage_counters_period_end", "usage_counters", ["period_end"])

    if not inspector.has_table("monetization_events"):
        op.create_table(
            "monetization_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subscription_profile_id", sa.Integer(), nullable=True),
            sa.Column("usage_counter_id", sa.Integer(), nullable=True),
            sa.Column("event_kind", monetization_event_kind_enum, nullable=False),
            sa.Column("event_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    existing_event_indexes = {item["name"] for item in inspector.get_indexes("monetization_events")}
    if "ix_monetization_events_id" not in existing_event_indexes:
        op.create_index("ix_monetization_events_id", "monetization_events", ["id"])
    if "ix_monetization_events_subscription_profile_id" not in existing_event_indexes:
        op.create_index(
            "ix_monetization_events_subscription_profile_id",
            "monetization_events",
            ["subscription_profile_id"],
        )
    if "ix_monetization_events_usage_counter_id" not in existing_event_indexes:
        op.create_index("ix_monetization_events_usage_counter_id", "monetization_events", ["usage_counter_id"])
    if "ix_monetization_events_event_kind" not in existing_event_indexes:
        op.create_index("ix_monetization_events_event_kind", "monetization_events", ["event_kind"])
    if "ix_monetization_events_created_at" not in existing_event_indexes:
        op.create_index("ix_monetization_events_created_at", "monetization_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_monetization_events_created_at", table_name="monetization_events")
    op.drop_index("ix_monetization_events_event_kind", table_name="monetization_events")
    op.drop_index("ix_monetization_events_usage_counter_id", table_name="monetization_events")
    op.drop_index("ix_monetization_events_subscription_profile_id", table_name="monetization_events")
    op.drop_index("ix_monetization_events_id", table_name="monetization_events")
    op.drop_table("monetization_events")

    op.drop_index("ix_usage_counters_period_end", table_name="usage_counters")
    op.drop_index("ix_usage_counters_period_start", table_name="usage_counters")
    op.drop_index("ix_usage_counters_metric", table_name="usage_counters")
    op.drop_index("ix_usage_counters_subscription_profile_id", table_name="usage_counters")
    op.drop_index("ix_usage_counters_id", table_name="usage_counters")
    op.drop_table("usage_counters")

    op.drop_index("ix_subscription_profiles_status", table_name="subscription_profiles")
    op.drop_index("ix_subscription_profiles_tier", table_name="subscription_profiles")
    op.drop_index("ix_subscription_profiles_subject", table_name="subscription_profiles")
    op.drop_index("ix_subscription_profiles_id", table_name="subscription_profiles")
    op.drop_table("subscription_profiles")
