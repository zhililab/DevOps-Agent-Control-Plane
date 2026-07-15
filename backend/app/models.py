from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.time_utils import utcnow_naive


def utcnow() -> datetime:
    return utcnow_naive()


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class SubscriptionTier(str, Enum):
    free = "free"
    pro = "pro"
    power = "power"


class SubscriptionStatus(str, Enum):
    inactive = "inactive"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"


class UsageMetric(str, Enum):
    workflow_runs = "workflow_runs"
    queued_runs = "queued_runs"


class MonetizationEventKind(str, Enum):
    subscription_changed = "subscription_changed"
    usage_recorded = "usage_recorded"
    usage_limit_reached = "usage_limit_reached"
    entitlement_checked = "entitlement_checked"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(32), default="en")
    preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    goals_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(64), default="work")
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus), default=TaskStatus.pending)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    source: Mapped[str] = mapped_column(String(64), default="manual")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class ReflectionEntry(Base):
    __tablename__ = "reflection_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today)
    completed_json: Mapped[str] = mapped_column(Text, default="[]")
    unfinished_json: Mapped[str] = mapped_column(Text, default="[]")
    blockers_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text)
    patterns: Mapped[str] = mapped_column(Text, default="")
    next_actions: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[str] = mapped_column(String(32), default="neutral")
    record_source: Mapped[str] = mapped_column(String(64), default="user", index=True)
    business_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"
    __table_args__ = (
        Index("ix_agent_run_logs_task_created_id", "task_type", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    record_source: Mapped[str] = mapped_column(String(64), default="user", index=True)
    business_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TechnicalAnalysis(Base):
    __tablename__ = "technical_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    record_source: Mapped[str] = mapped_column(String(64), default="user", index=True)
    business_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NoteEntry(Base):
    __tablename__ = "note_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowOrchestration(Base):
    __tablename__ = "workflow_orchestrations"
    __table_args__ = (
        Index("ix_workflow_orchestrations_created_id", "created_at", "id"),
        Index("ix_workflow_orchestrations_status_created_id", "status", "created_at", "id"),
        Index("ix_workflow_orchestrations_tier_created_id", "subscription_tier", "created_at", "id"),
        Index("ix_workflow_orchestrations_team_created_id", "team_subject", "created_at", "id"),
        Index(
            "ix_workflow_orchestrations_status_tier_created_id",
            "status",
            "subscription_tier",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    entry_source: Mapped[str] = mapped_column(String(64), default="manual")
    subscription_tier: Mapped[str] = mapped_column(String(16), default="pro", index=True)
    team_subject: Mapped[str] = mapped_column(String(120), default="", index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    approval_actor: Mapped[str] = mapped_column(String(120), default="")
    approval_note: Mapped[str] = mapped_column(Text, default="")
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowStepRun(Base):
    __tablename__ = "workflow_step_runs"
    __table_args__ = (
        Index("ix_workflow_step_runs_orchestration_id_id", "orchestration_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    orchestration_id: Mapped[int] = mapped_column(Integer, index=True)
    step_name: Mapped[str] = mapped_column(String(120))
    agent_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="success")
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    audit_json: Mapped[str] = mapped_column(Text, default="{}")
    fallback_action: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowQueueJob(Base):
    __tablename__ = "workflow_queue_jobs"
    __table_args__ = (
        Index("ix_workflow_queue_jobs_updated_id", "updated_at", "id"),
        Index("ix_workflow_queue_jobs_status_updated_id", "status", "updated_at", "id"),
        Index("ix_workflow_queue_jobs_team_updated_id", "team_subject", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    orchestration_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    team_subject: Mapped[str] = mapped_column(String(120), default="", index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    approval_actor: Mapped[str] = mapped_column(String(120), default="")
    approval_note: Mapped[str] = mapped_column(Text, default="")
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowQueueEvent(Base):
    __tablename__ = "workflow_queue_events"
    __table_args__ = (
        Index("ix_workflow_queue_events_job_created_id", "queue_job_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    queue_job_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"
    __table_args__ = (
        UniqueConstraint("checkpoint_uid", name="uq_workflow_checkpoints_checkpoint_uid"),
        Index("ix_workflow_checkpoints_orchestration_created_id", "orchestration_id", "created_at", "id"),
        Index("ix_workflow_checkpoints_queue_job_created_id", "queue_job_id", "created_at", "id"),
        Index("ix_workflow_checkpoints_entity_created_id", "entity_type", "entity_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checkpoint_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    orchestration_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    queue_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    checkpoint_type: Mapped[str] = mapped_column(String(80), index=True)
    step_name: Mapped[str] = mapped_column(String(120), default="")
    step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_sha256: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class SubscriptionProfile(Base):
    __tablename__ = "subscription_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(120), index=True)
    tier: Mapped[SubscriptionTier] = mapped_column(
        SqlEnum(SubscriptionTier, native_enum=False),
        default=SubscriptionTier.free,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SqlEnum(SubscriptionStatus, native_enum=False),
        default=SubscriptionStatus.inactive,
        index=True,
    )
    billing_provider: Mapped[str] = mapped_column(String(32), default="manual")
    external_customer_id: Mapped[str] = mapped_column(String(160), default="")
    external_subscription_id: Mapped[str] = mapped_column(String(160), default="")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    entitlements_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_profile_id: Mapped[int] = mapped_column(Integer, index=True)
    metric: Mapped[UsageMetric] = mapped_column(SqlEnum(UsageMetric, native_enum=False), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    used: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MonetizationEvent(Base):
    __tablename__ = "monetization_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    usage_counter_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_kind: Mapped[MonetizationEventKind] = mapped_column(
        SqlEnum(MonetizationEventKind, native_enum=False),
        index=True,
    )
    event_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class HistoryEvent(Base):
    __tablename__ = "history_events"
    __table_args__ = (
        UniqueConstraint("event_uid", name="uq_history_events_event_uid"),
        Index("ix_history_events_entity_occurrence", "entity_type", "entity_id", "occurred_at", "id"),
        Index("ix_history_events_correlation_occurrence", "correlation_id", "occurred_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_uid: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(120), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    source_table: Mapped[str] = mapped_column(String(120), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    correlation_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_sha256: Mapped[str] = mapped_column(String(64))
    previous_event_sha256: Mapped[str] = mapped_column(String(64), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    integrity_status: Mapped[str] = mapped_column(String(32), default="valid", index=True)
    integrity_error: Mapped[str] = mapped_column(Text, default="")


class LlmInvocation(Base):
    __tablename__ = "llm_invocations"
    __table_args__ = (
        Index("ix_llm_invocations_orchestration_created_id", "orchestration_id", "created_at", "id"),
        Index("ix_llm_invocations_evaluation_created_id", "evaluation_run_id", "created_at", "id"),
        Index("ix_llm_invocations_provider_model_created_id", "provider", "model", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    orchestration_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    evaluation_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    evaluation_case_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(160), index=True)
    prompt_version: Mapped[str] = mapped_column(String(80), index=True)
    request_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    decision: Mapped[str] = mapped_column(String(32), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_microusd: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(160), index=True)
    prompt_version: Mapped[str] = mapped_column(String(80), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="deterministic", index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    false_positive_count: Mapped[int] = mapped_column(Integer, default=0)
    false_negative_count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    average_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_microusd: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EvaluationCaseResult(Base):
    __tablename__ = "evaluation_case_results"
    __table_args__ = (
        UniqueConstraint("evaluation_run_id", "case_id", name="uq_evaluation_case_results_run_case"),
        Index("ix_evaluation_case_results_run_id_id", "evaluation_run_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluation_run_id: Mapped[int] = mapped_column(Integer, index=True)
    invocation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    case_id: Mapped[str] = mapped_column(String(80), index=True)
    expected_decision: Mapped[str] = mapped_column(String(32), index=True)
    actual_decision: Mapped[str] = mapped_column(String(32), index=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class DecisionFeedback(Base):
    __tablename__ = "decision_feedback"
    __table_args__ = (
        Index("ix_decision_feedback_case_created_id", "evaluation_case_result_id", "created_at", "id"),
        Index("ix_decision_feedback_orchestration_created_id", "orchestration_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluation_case_result_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    orchestration_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    verdict: Mapped[str] = mapped_column(String(32), index=True)
    corrected_decision: Mapped[str] = mapped_column(String(32), default="")
    actor: Mapped[str] = mapped_column(String(120), default="reviewer")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class PilotMeasurement(Base):
    __tablename__ = "pilot_measurements"
    __table_args__ = (
        Index("ix_pilot_measurements_subject_metric_phase", "subject", "metric", "phase", "measured_at", "id"),
        Index("ix_pilot_measurements_team_metric_phase", "team_subject", "metric", "phase", "measured_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(120), default="", index=True)
    team_subject: Mapped[str] = mapped_column(String(120), default="", index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    phase: Mapped[str] = mapped_column(String(16), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    sample_size: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(64), default="observed")
    notes: Mapped[str] = mapped_column(Text, default="")
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
