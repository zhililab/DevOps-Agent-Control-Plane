"""add llm evaluation, feedback, and pilot measurement tables

Revision ID: 0018_add_llm_evaluation_feedback
Revises: 0017_add_ai_pr_release_gate_template
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "0018_add_llm_evaluation_feedback"
down_revision = "0017_add_ai_pr_release_gate_template"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_invocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("orchestration_id", sa.Integer(), nullable=True),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=True),
        sa.Column("evaluation_case_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("request_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("risks_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_microusd", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_invocations_id", "llm_invocations", ["id"])
    op.create_index("ix_llm_invocations_orchestration_id", "llm_invocations", ["orchestration_id"])
    op.create_index("ix_llm_invocations_evaluation_run_id", "llm_invocations", ["evaluation_run_id"])
    op.create_index("ix_llm_invocations_evaluation_case_id", "llm_invocations", ["evaluation_case_id"])
    op.create_index("ix_llm_invocations_request_sha256", "llm_invocations", ["request_sha256"])
    op.create_index("ix_llm_invocations_status", "llm_invocations", ["status"])
    op.create_index("ix_llm_invocations_created_at", "llm_invocations", ["created_at"])
    op.create_index(
        "ix_llm_invocations_orchestration_created_id",
        "llm_invocations",
        ["orchestration_id", "created_at", "id"],
    )
    op.create_index(
        "ix_llm_invocations_evaluation_created_id",
        "llm_invocations",
        ["evaluation_run_id", "created_at", "id"],
    )
    op.create_index(
        "ix_llm_invocations_provider_model_created_id",
        "llm_invocations",
        ["provider", "model", "created_at", "id"],
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="deterministic"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_positive_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_negative_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_microusd", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "dataset_version", "provider", "model", "prompt_version", "mode", "status", "created_at"):
        op.create_index(f"ix_evaluation_runs_{column}", "evaluation_runs", [column])

    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("invocation_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.String(length=80), nullable=False),
        sa.Column("expected_decision", sa.String(length=32), nullable=False),
        sa.Column("actual_decision", sa.String(length=32), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "case_id", name="uq_evaluation_case_results_run_case"),
    )
    for column in ("id", "evaluation_run_id", "invocation_id", "case_id", "expected_decision", "actual_decision", "is_correct", "created_at"):
        op.create_index(f"ix_evaluation_case_results_{column}", "evaluation_case_results", [column])
    op.create_index(
        "ix_evaluation_case_results_run_id_id",
        "evaluation_case_results",
        ["evaluation_run_id", "id"],
    )

    op.create_table(
        "decision_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_case_result_id", sa.Integer(), nullable=True),
        sa.Column("orchestration_id", sa.Integer(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("corrected_decision", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="reviewer"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "evaluation_case_result_id", "orchestration_id", "verdict", "created_at"):
        op.create_index(f"ix_decision_feedback_{column}", "decision_feedback", [column])
    op.create_index(
        "ix_decision_feedback_case_created_id",
        "decision_feedback",
        ["evaluation_case_result_id", "created_at", "id"],
    )
    op.create_index(
        "ix_decision_feedback_orchestration_created_id",
        "decision_feedback",
        ["orchestration_id", "created_at", "id"],
    )

    op.create_table(
        "pilot_measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("team_subject", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="observed"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "subject", "team_subject", "metric", "phase", "measured_at", "created_at"):
        op.create_index(f"ix_pilot_measurements_{column}", "pilot_measurements", [column])
    op.create_index(
        "ix_pilot_measurements_subject_metric_phase",
        "pilot_measurements",
        ["subject", "metric", "phase", "measured_at", "id"],
    )
    op.create_index(
        "ix_pilot_measurements_team_metric_phase",
        "pilot_measurements",
        ["team_subject", "metric", "phase", "measured_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("pilot_measurements")
    op.drop_table("decision_feedback")
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
    op.drop_table("llm_invocations")
