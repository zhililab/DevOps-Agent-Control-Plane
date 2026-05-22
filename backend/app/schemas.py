from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from app.time_utils import format_utc_datetime


class BaseModel(PydanticBaseModel):
    @field_serializer("*", when_used="json")
    def serialize_utc_datetimes(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return format_utc_datetime(value)
        return value


class UserProfileBase(BaseModel):
    name: str
    role: str
    language: str = "en"
    preferences: dict[str, Any] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    language: str | None = None
    preferences: dict[str, Any] | None = None
    goals: list[str] | None = None


class UserProfileRead(UserProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    title: str
    domain: str = "work"
    status: str = "pending"
    priority: int = Field(default=3, ge=1, le=5)
    source: str = "manual"
    context: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    domain: str | None = None
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    source: str | None = None
    context: dict[str, Any] | None = None


class TaskRead(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReflectionEntryBase(BaseModel):
    entry_date: date
    summary: str
    patterns: str = ""
    next_actions: str = ""
    mood: str = "neutral"


class ReflectionEntryCreate(ReflectionEntryBase):
    pass


class ReflectionEntryUpdate(BaseModel):
    summary: str | None = None
    patterns: str | None = None
    next_actions: str | None = None
    mood: str | None = None


class ReflectionEntryRead(ReflectionEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunLogRead(BaseModel):
    id: int
    task_type: str
    input_summary: str
    output_summary: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanGenerateRequest(BaseModel):
    focus: str | None = None
    tasks: list[TaskCreate] = Field(default_factory=list)


class PlanGenerateResponse(BaseModel):
    plan_date: date
    focus: str
    priorities: list[str]
    tasks: list[TaskRead]
    notes: str


class DailyContextInput(BaseModel):
    tasks: list[str] = Field(default_factory=list, max_length=50)
    meetings: list[str] = Field(default_factory=list, max_length=50)
    blockers: list[str] = Field(default_factory=list, max_length=50)
    priorities: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("tasks", "meetings", "blockers", "priorities")
    @classmethod
    def validate_daily_context_items(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value.strip()) > 300:
                raise ValueError("Each item must be 300 characters or fewer.")
        return values


class DailyPlanStructured(BaseModel):
    top_priorities: list[str]
    recommended_order: list[str]
    risks_and_reminders: list[str]
    next_actions: list[str]
    status_summary: str


class DailyPlanSavedResponse(BaseModel):
    id: int
    plan_date: date
    context: DailyContextInput
    plan: DailyPlanStructured
    created_at: datetime
    record_source: str = "user"
    business_timezone: str = "Asia/Shanghai"


class DailyPlanHistoryResponse(BaseModel):
    items: list[DailyPlanSavedResponse]


class DailyReflectionInput(BaseModel):
    completed: list[str] = Field(default_factory=list, max_length=50)
    unfinished: list[str] = Field(default_factory=list, max_length=50)
    blockers: list[str] = Field(default_factory=list, max_length=50)
    mood_or_notes: str = Field(default="", max_length=2000)

    @field_validator("completed", "unfinished", "blockers")
    @classmethod
    def validate_reflection_items(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value.strip()) > 300:
                raise ValueError("Each item must be 300 characters or fewer.")
        return values


class DailyReflectionSummary(BaseModel):
    day_summary: str
    unfinished_items: list[str]
    pattern_hints: list[str]
    tomorrow_suggestions: list[str]


class DailyReflectionSavedResponse(BaseModel):
    id: int
    entry_date: date
    input: DailyReflectionInput
    summary: DailyReflectionSummary
    created_at: datetime
    record_source: str = "user"
    business_timezone: str = "Asia/Shanghai"


class DailyReflectionHistoryResponse(BaseModel):
    items: list[DailyReflectionSavedResponse]


class TechnicalAnalysisInput(BaseModel):
    logs: str = Field(default="", max_length=10000)
    errors: list[str] = Field(default_factory=list, max_length=60)
    code_snippets: list[str] = Field(default_factory=list, max_length=60)
    issue_description: str = Field(default="", max_length=2000)

    @field_validator("errors", "code_snippets")
    @classmethod
    def validate_analysis_items(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value.strip()) > 500:
                raise ValueError("Each item must be 500 characters or fewer.")
        return values

    @model_validator(mode="after")
    def ensure_at_least_one_signal(self) -> "TechnicalAnalysisInput":
        has_logs = bool(self.logs.strip())
        has_errors = any(error.strip() for error in self.errors)
        has_code = any(snippet.strip() for snippet in self.code_snippets)
        has_issue = bool(self.issue_description.strip())
        if not (has_logs or has_errors or has_code or has_issue):
            raise ValueError(
                "Provide at least one of logs, errors, code_snippets, or issue_description."
            )
        return self


class StructuredAnalysisResult(BaseModel):
    problem_statement: str
    likely_causes: list[str]
    validation_steps: list[str]
    fix_options: list[str]
    risks: list[str]
    follow_up_tasks: list[str]


class TechnicalAnalysisOutput(StructuredAnalysisResult):
    pass


class TechnicalAnalysisSavedResponse(BaseModel):
    id: int
    analysis_date: date
    input: TechnicalAnalysisInput
    output: TechnicalAnalysisOutput
    created_at: datetime
    record_source: str = "user"
    business_timezone: str = "Asia/Shanghai"


class TechnicalAnalysisHistoryResponse(BaseModel):
    items: list[TechnicalAnalysisSavedResponse]


class NoteEntryBase(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("title", "content")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be empty.")
        return value


class NoteEntryCreate(NoteEntryBase):
    pass


class NoteEntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class NoteEntryRead(NoteEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateBase(BaseModel):
    name: str
    description: str = ""
    body: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("name", "body")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be empty.")
        return value


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    body: str | None = None
    tags: list[str] | None = None


class PromptTemplateRead(PromptTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateImportJsonRequest(BaseModel):
    items: list[PromptTemplateCreate] = Field(default_factory=list)
    upsert_by_name: bool = True
    use_builtin: bool = False


class PromptTemplateImportSqlRequest(BaseModel):
    sql: str = ""
    reset_existing: bool = False
    use_builtin: bool = False

    @model_validator(mode="after")
    def ensure_sql_source(self) -> "PromptTemplateImportSqlRequest":
        if not self.use_builtin and not self.sql.strip():
            raise ValueError("Provide SQL content or set use_builtin=true.")
        return self


class PromptTemplateImportResponse(BaseModel):
    mode: str
    imported: int
    updated: int
    skipped: int
    total: int


SubscriptionTier = Literal["free", "pro", "power"]
OrchestrationStatus = Literal["running", "success", "partial_success", "failed", "canceled"]
StepStatus = Literal["success", "failed", "skipped"]
AgentType = Literal["planner", "analyzer", "reviewer"]
WorkflowTemplateRiskLevel = Literal["low", "medium", "high", "critical"]


class WorkflowStepDefinition(BaseModel):
    step_name: str
    agent_type: AgentType
    enabled: bool = True


class WorkflowTemplatePolicy(BaseModel):
    required_tier: SubscriptionTier = "pro"
    risk_level: WorkflowTemplateRiskLevel = "medium"
    approval_required: bool = False
    allowed_tool_scopes: list[str] = Field(default_factory=lambda: ["none"], max_length=10)
    billable_work_units: int = Field(default=1, ge=1, le=100)

    @field_validator("allowed_tool_scopes")
    @classmethod
    def validate_tool_scopes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            scope = value.strip().lower()
            if not scope:
                continue
            if len(scope) > 80:
                raise ValueError("Tool scopes must be 80 characters or fewer.")
            if scope not in normalized:
                normalized.append(scope)
        return normalized or ["none"]


class WorkflowTemplateBase(BaseModel):
    name: str
    description: str = ""
    steps: list[WorkflowStepDefinition] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=20)
    policy: WorkflowTemplatePolicy | None = None
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be empty.")
        return value

    @model_validator(mode="after")
    def ensure_steps_not_empty(self) -> "WorkflowTemplateBase":
        active_steps = [step for step in self.steps if step.enabled]
        if not active_steps:
            raise ValueError("At least one enabled step is required.")
        return self


class WorkflowTemplateCreate(WorkflowTemplateBase):
    pass


class WorkflowTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[WorkflowStepDefinition] | None = None
    tags: list[str] | None = None
    policy: WorkflowTemplatePolicy | None = None
    enabled: bool | None = None


class WorkflowTemplateRead(WorkflowTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateImportRequest(BaseModel):
    items: list[WorkflowTemplateCreate] = Field(default_factory=list)
    upsert_by_name: bool = True


class WorkflowTemplateImportResponse(BaseModel):
    imported: int
    updated: int
    skipped: int
    total: int


class WorkflowAuditBlock(BaseModel):
    conclusion: str
    evidence: str
    risk: str
    next_action: str

    @field_validator("conclusion", "evidence", "risk", "next_action")
    @classmethod
    def reject_blank_text_block(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be empty.")
        return value


class WorkflowStepRunRead(BaseModel):
    id: int
    step_name: str
    agent_type: AgentType
    status: StepStatus
    input_summary: str
    output_summary: str
    audit: WorkflowAuditBlock
    fallback_action: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int


class WorkflowOrchestrationSummary(BaseModel):
    conclusion: str
    risks: list[str]
    next_actions: list[str]


class HistoryIntegritySummary(BaseModel):
    entity_type: str
    entity_id: str
    integrity_status: str
    event_count: int


class WorkflowOrchestrationRunRequest(BaseModel):
    entry_source: str = "manual"
    template_id: int | None = None
    steps: list[WorkflowStepDefinition] | None = None
    daily_context: DailyContextInput | None = None
    technical_input: TechnicalAnalysisInput | None = None
    reflection_input: DailyReflectionInput | None = None
    persist_knowledge: bool = True
    persist_template: bool = False
    approval_confirmed: bool = False

    @model_validator(mode="after")
    def ensure_template_or_steps(self) -> "WorkflowOrchestrationRunRequest":
        if self.template_id is not None:
            return self
        if self.steps and any(step.enabled for step in self.steps):
            return self
        raise ValueError("Provide template_id or at least one enabled step.")


class WorkflowOrchestrationRead(BaseModel):
    id: int
    status: OrchestrationStatus
    duration_ms: int
    entry_source: str
    subscription_tier: SubscriptionTier
    summary: WorkflowOrchestrationSummary
    steps: list[WorkflowStepRunRead]
    ledger_integrity: HistoryIntegritySummary | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowOrchestrationHistoryResponse(BaseModel):
    items: list[WorkflowOrchestrationRead]


class WorkflowOrchestrationMetricsResponse(BaseModel):
    period_days: int
    total_runs: int
    weekly_active_orchestrations: int
    partial_success_rate: float
    average_duration_ms: int
    billable_work_units: int
    successful_audited_workflows: int
    approval_required_blocks: int
    template_policy_upgrade_blocks: int


class HistoryEventRead(BaseModel):
    id: int
    event_uid: str
    entity_type: str
    entity_id: str
    event_type: str
    event_version: int
    source_table: str
    source_id: str
    correlation_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_sha256: str
    previous_event_sha256: str
    occurred_at: datetime
    created_at: datetime
    integrity_status: str
    integrity_error: str


class HistoryIntegrityResponse(BaseModel):
    entity_type: str
    entity_id: str
    integrity_status: str
    event_count: int
    events: list[HistoryEventRead]


class EntitlementBootstrapResponse(BaseModel):
    token: str
    tier: SubscriptionTier
    expires_at: datetime


QueueJobStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]


class WorkflowQueueRunResponse(BaseModel):
    job_id: int
    status: QueueJobStatus
    attempts: int
    max_attempts: int


class WorkflowQueueEventRead(BaseModel):
    id: int
    queue_job_id: int
    event_type: str
    status: QueueJobStatus
    detail: str
    created_at: datetime


class WorkflowQueueJobRead(BaseModel):
    id: int
    status: QueueJobStatus
    attempts: int
    max_attempts: int
    cancel_requested: bool
    orchestration_id: int | None
    error_message: str
    created_at: datetime
    updated_at: datetime
    events: list[WorkflowQueueEventRead] = Field(default_factory=list)


class WorkflowQueueHistoryResponse(BaseModel):
    items: list[WorkflowQueueJobRead]


MonetizationTier = Literal["free", "pro", "power"]
MonetizationSubscriptionStatus = Literal["inactive", "active", "past_due", "canceled"]
UsageMetric = Literal["workflow_runs", "queued_runs"]
MonetizationEventKind = Literal[
    "subscription_changed",
    "usage_recorded",
    "usage_limit_reached",
    "entitlement_checked",
]


class SubscriptionProfileRead(BaseModel):
    id: int
    subject: str
    tier: MonetizationTier
    status: MonetizationSubscriptionStatus
    billing_provider: str
    external_customer_id: str
    external_subscription_id: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    entitlements: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageCounterRead(BaseModel):
    id: int
    subscription_profile_id: int
    metric: UsageMetric
    period_start: date
    period_end: date
    used: int
    limit: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonetizationEventRead(BaseModel):
    id: int
    subscription_profile_id: int | None
    usage_counter_id: int | None
    event_kind: MonetizationEventKind
    event: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualCheckoutRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=120)
    target_tier: MonetizationTier
    billing_provider: str = Field(default="manual", min_length=1, max_length=32)

    @field_validator("subject", "billing_provider")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty.")
        return stripped


class SubscriptionCancelRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=120)

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Subject cannot be empty.")
        return stripped


class SubscriptionLifecycleResponse(BaseModel):
    profile: SubscriptionProfileRead
    counters: list[UsageCounterRead] = Field(default_factory=list)
    event: MonetizationEventRead


class MonetizationObservabilityResponse(BaseModel):
    profile: SubscriptionProfileRead | None = None
    counters: list[UsageCounterRead] = Field(default_factory=list)
    recent_events: list[MonetizationEventRead] = Field(default_factory=list)
