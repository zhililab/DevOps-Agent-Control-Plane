from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    # Keep UTC semantics but return a naive datetime so it is compatible with
    # DateTime(timezone=False) columns across SQLite and PostgreSQL.
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TechnicalAnalysis(Base):
    __tablename__ = "technical_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    entry_source: Mapped[str] = mapped_column(String(64), default="manual")
    subscription_tier: Mapped[str] = mapped_column(String(16), default="pro", index=True)
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowStepRun(Base):
    __tablename__ = "workflow_step_runs"

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    orchestration_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WorkflowQueueEvent(Base):
    __tablename__ = "workflow_queue_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    queue_job_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")
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
