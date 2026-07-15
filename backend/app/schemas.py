from datetime import date, datetime
import re
from typing import Any, Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from app.time_utils import format_utc_datetime


_AUTH_PAIR_PATTERN = re.compile(
    r"(?i)(authorization)\s*[:=]\s*(Bearer\s+[A-Za-z0-9\-._~+/]+=*|[^,\n;]+)"
)
_SECRET_PAIR_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*([^,\s;\n]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]+=*)")


def _sanitize_user_text(value: str) -> str:
    text = value.strip()
    text = _AUTH_PAIR_PATTERN.sub(lambda match: f"{match.group(1)}=<redacted>", text)
    text = _SECRET_PAIR_PATTERN.sub(lambda match: f"{match.group(1)}=<redacted>", text)
    return _BEARER_PATTERN.sub("Bearer <redacted>", text)


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


class ReleaseGatePrCiInput(BaseModel):
    pr_url: str = Field(default="", max_length=500)
    pr_diff_summary: str = Field(default="", max_length=2000)
    ci_log_summary: str = Field(default="", max_length=4000)
    target_environment: str = Field(default="", max_length=200)
    change_risk: str = Field(default="", max_length=1000)

    @field_validator("pr_url", "pr_diff_summary", "ci_log_summary", "target_environment", "change_risk")
    @classmethod
    def sanitize_adapter_text(cls, value: str) -> str:
        return _sanitize_user_text(value)


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


class WorkflowRunPolicyGate(BaseModel):
    template_id: int | None = None
    template_name: str = ""
    required_tier: SubscriptionTier
    risk_level: Literal["low", "medium", "high", "critical"]
    approval_required: bool = False
    approval_confirmed: bool = False
    allowed_tool_scopes: list[str] = Field(default_factory=list)
    billable_work_units: int = 1
    decision: str = "needs human review"


class WorkflowRoiEvidence(BaseModel):
    review_time_saved_minutes: int = 0
    audit_time_saved_minutes: int = 0
    blocked_risk_count: int = 0
    blocked_risk_value_usd: int = 0
    estimated_customer_value_usd: int = 0
    billable_work_units: int = 1
    assumptions: list[str] = Field(default_factory=list)


class HistoryIntegritySummary(BaseModel):
    entity_type: str
    entity_id: str
    integrity_status: str
    event_count: int


class WorkflowOrchestrationRunRequest(BaseModel):
    entry_source: str = "manual"
    pilot_scenario_id: str | None = Field(default=None, max_length=80)
    team_subject: str = Field(default="demo-team", max_length=120)
    requested_by: str = Field(default="sre-lead", max_length=120)
    approval_actor: str = Field(default="release-manager", max_length=120)
    approval_note: str = Field(
        default="Approved for trusted DevOps workflow execution.",
        max_length=1000,
    )
    template_id: int | None = None
    steps: list[WorkflowStepDefinition] | None = None
    daily_context: DailyContextInput | None = None
    technical_input: TechnicalAnalysisInput | None = None
    reflection_input: DailyReflectionInput | None = None
    release_gate_input: ReleaseGatePrCiInput | None = None
    persist_knowledge: bool = True
    persist_template: bool = False
    approval_confirmed: bool = False
    use_llm_provider: bool = False

    @model_validator(mode="after")
    def ensure_template_or_steps(self) -> "WorkflowOrchestrationRunRequest":
        if self.template_id is not None:
            return self
        if self.steps and any(step.enabled for step in self.steps):
            return self
        raise ValueError("Provide template_id or at least one enabled step.")


class PilotScenarioRead(BaseModel):
    id: str
    name: str
    description: str = ""
    expected_gate_behavior: Literal["approve", "block", "needs human review"]
    required_tier: SubscriptionTier
    approval_required: bool
    approval_confirmed: bool = False
    recommended_template_name: str = "AI-generated PR Release Gate"
    release_gate_input: ReleaseGatePrCiInput
    daily_context: DailyContextInput
    technical_input: TechnicalAnalysisInput
    reflection_input: DailyReflectionInput
    success_signal: str


class PilotScenarioListResponse(BaseModel):
    items: list[PilotScenarioRead]


class WorkflowOrchestrationRead(BaseModel):
    id: int
    status: OrchestrationStatus
    duration_ms: int
    entry_source: str
    pilot_scenario_id: str | None = None
    subscription_tier: SubscriptionTier
    team_subject: str = ""
    requested_by: str = ""
    approval_actor: str = ""
    approval_note: str = ""
    policy_gate: WorkflowRunPolicyGate | None = None
    billable_work_units: int = 1
    roi_evidence: WorkflowRoiEvidence | None = None
    summary: WorkflowOrchestrationSummary
    steps: list[WorkflowStepRunRead]
    ledger_integrity: HistoryIntegritySummary | None = None
    checkpoint_count: int = 0
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
    approved_runs: int = 0
    checkpointed_runs: int = 0
    failed_jobs_needing_owner: int = 0


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


class WorkflowCheckpointRead(BaseModel):
    id: int
    checkpoint_uid: str
    entity_type: str
    entity_id: str
    orchestration_id: int | None
    queue_job_id: int | None
    checkpoint_type: str
    step_name: str
    step_index: int | None
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_sha256: str
    created_by: str
    created_at: datetime
    integrity_status: str
    integrity_error: str


class WorkflowCheckpointHistoryResponse(BaseModel):
    items: list[WorkflowCheckpointRead]


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
    team_subject: str = ""
    requested_by: str = ""
    approval_actor: str = ""
    approval_note: str = ""
    error_message: str
    created_at: datetime
    updated_at: datetime
    events: list[WorkflowQueueEventRead] = Field(default_factory=list)
    checkpoints: list[WorkflowCheckpointRead] = Field(default_factory=list)


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


class CommercialMetricsSubscriptionSummary(BaseModel):
    active_subjects: int
    profile_count: int
    tier_distribution: dict[MonetizationTier, int]
    status_distribution: dict[MonetizationSubscriptionStatus, int]


class CommercialMetricsUsageSummary(BaseModel):
    workflow_runs_used: int
    workflow_runs_limit: int
    queued_runs_used: int
    queued_runs_limit: int
    usage_subjects: int


class CommercialMetricsPlanUsage(BaseModel):
    workflow_runs_used: int
    workflow_runs_limit: int
    queued_runs_used: int
    queued_runs_limit: int
    period_start: date | None = None
    period_end: date | None = None


class CommercialMetricsEventSummary(BaseModel):
    action: str
    count: int


class CommercialMetricsPolicyBlocks(BaseModel):
    approval_required: int
    upgrade_required: int
    quota_exceeded: int
    total: int


class CommercialMetricsBillableWorkUnits(BaseModel):
    total: int
    audited_workflows: int
    average_per_run: float


class CommercialMetricsRoiTemplateBreakdown(BaseModel):
    template_id: int | None = None
    template_name: str
    runs: int
    billable_work_units: int
    estimated_customer_value_usd: int


class CommercialMetricsRoiSummary(BaseModel):
    runs_with_roi: int
    estimated_customer_value_usd: int
    review_time_saved_minutes: int
    audit_time_saved_minutes: int
    blocked_risk_count: int
    blocked_risk_value_usd: int
    billable_work_units: int
    work_units_by_template: list[CommercialMetricsRoiTemplateBreakdown] = Field(default_factory=list)


class PilotScenarioCompletionRead(BaseModel):
    id: str
    name: str
    status: Literal["missing", "needs evidence", "completed"]
    expected_gate_behavior: Literal["approve", "block", "needs human review"]
    required_tier: SubscriptionTier
    completed_runs: int = 0
    evidence_exportable_runs: int = 0
    ledger_valid_runs: int = 0
    checkpointed_runs: int = 0
    approval_metadata_complete: bool = False
    latest_orchestration_id: int | None = None


class PilotScenarioCompletionSummary(BaseModel):
    total: int
    completed: int
    needs_evidence: int
    missing: int
    next_scenario_id: str | None = None
    ready_for_buyer_review: bool = False


class PilotPowerUpgradeEvidence(BaseModel):
    power_required_runs: int = 0
    approval_required_runs: int = 0
    blocked_or_needs_review_runs: int = 0
    evidence_exportable_runs: int = 0
    ledger_valid_runs: int = 0
    estimated_value_usd: int = 0
    review_audit_time_saved_minutes: int = 0
    recommendation: str


class CommercialMetricsTopTemplate(BaseModel):
    template_id: int | None = None
    template_name: str
    runs: int
    billable_work_units: int
    required_tier: MonetizationTier
    risk_level: WorkflowTemplateRiskLevel
    approval_required: bool


class CommercialMetricsTrendPoint(BaseModel):
    date: str
    billable_work_units: int
    audited_workflows: int
    policy_blocks: int


class CommercialMetricsAnomalyHint(BaseModel):
    code: str
    severity: Literal["info", "warning", "critical"] = "info"
    message: str


class CommercialMetricsResponse(BaseModel):
    window_days: int
    generated_at: datetime
    subject: str | None = None
    subscription_summary: CommercialMetricsSubscriptionSummary
    usage_summary: CommercialMetricsUsageSummary
    plan_usage: CommercialMetricsPlanUsage
    commercial_events: list[CommercialMetricsEventSummary] = Field(default_factory=list)
    policy_blocks: CommercialMetricsPolicyBlocks
    billable_work_units: CommercialMetricsBillableWorkUnits
    roi_summary: CommercialMetricsRoiSummary
    top_templates: list[CommercialMetricsTopTemplate] = Field(default_factory=list)
    trend: list[CommercialMetricsTrendPoint] = Field(default_factory=list)
    anomaly_hints: list[CommercialMetricsAnomalyHint] = Field(default_factory=list)


class PilotReadinessReportResponse(BaseModel):
    window_days: int
    generated_at: datetime
    subject: str | None = None
    team_subject: str | None = None
    status: Literal["ready", "needs evidence", "needs approval metadata"]
    runs_completed: int
    evidence_exportable_runs: int
    ledger_valid_runs: int
    checkpointed_runs: int
    approval_required_runs: int
    blocked_or_needs_review_runs: int
    estimated_value_usd: int
    review_time_saved_minutes: int
    audit_time_saved_minutes: int
    metadata_completeness: float
    missing_metadata_runs: int
    scenario_statuses: list[PilotScenarioCompletionRead] = Field(default_factory=list)
    scenario_completion: PilotScenarioCompletionSummary
    power_upgrade_evidence: PilotPowerUpgradeEvidence
    success_criteria: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class WorkflowEvidenceExportResponse(BaseModel):
    orchestration_id: int
    generated_at: datetime
    format: Literal["markdown"] = "markdown"
    markdown: str
    data: dict[str, Any] = Field(default_factory=dict)


class PilotCloseoutReportResponse(BaseModel):
    window_days: int
    generated_at: datetime
    subject: str | None = None
    team_subject: str | None = None
    status: Literal["ready", "needs evidence", "needs approval metadata"]
    markdown: str
    data: dict[str, Any] = Field(default_factory=dict)


ReleaseGateDecision = Literal["approve", "block", "needs human review"]


class LlmProviderStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    provider: str
    model: str
    prompt_version: str
    base_url_host: str
    write_protected: bool
    deterministic_gate_remains_authoritative: bool = True


class LlmInvocationRead(BaseModel):
    id: int
    orchestration_id: int | None = None
    evaluation_run_id: int | None = None
    evaluation_case_id: str = ""
    provider: str
    model: str
    prompt_version: str
    request_sha256: str
    status: str
    decision: str
    confidence: float
    rationale: str
    risks: list[str] = Field(default_factory=list)
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float
    error_message: str
    created_at: datetime


class LlmInvocationListResponse(BaseModel):
    items: list[LlmInvocationRead]


class EvaluationCaseRead(BaseModel):
    id: str
    name: str
    category: str
    expected_decision: ReleaseGateDecision
    release_gate_input: ReleaseGatePrCiInput
    rationale: str


class EvaluationCaseListResponse(BaseModel):
    dataset_version: str
    items: list[EvaluationCaseRead]


class EvaluationRunRequest(BaseModel):
    mode: Literal["deterministic", "live"] = "deterministic"
    case_ids: list[str] = Field(default_factory=list, max_length=30)


class EvaluationCaseResultRead(BaseModel):
    id: int
    case_id: str
    expected_decision: ReleaseGateDecision
    actual_decision: ReleaseGateDecision
    is_correct: bool
    confidence: float
    rationale: str
    latency_ms: int


class EvaluationRunRead(BaseModel):
    id: int
    dataset_version: str
    provider: str
    model: str
    prompt_version: str
    mode: Literal["deterministic", "live"]
    status: str
    case_count: int
    correct_count: int
    false_positive_count: int
    false_negative_count: int
    accuracy: float
    average_latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    created_at: datetime
    completed_at: datetime | None = None
    results: list[EvaluationCaseResultRead] = Field(default_factory=list)


class DecisionFeedbackCreate(BaseModel):
    evaluation_case_result_id: int | None = None
    orchestration_id: int | None = None
    verdict: Literal["accepted", "rejected", "corrected"]
    corrected_decision: ReleaseGateDecision | None = None
    actor: str = Field(default="reviewer", min_length=1, max_length=120)
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_feedback_target_and_correction(self) -> "DecisionFeedbackCreate":
        if self.evaluation_case_result_id is None and self.orchestration_id is None:
            raise ValueError("Provide evaluation_case_result_id or orchestration_id.")
        if self.verdict == "corrected" and self.corrected_decision is None:
            raise ValueError("corrected_decision is required when verdict is corrected.")
        return self


class DecisionFeedbackRead(BaseModel):
    id: int
    evaluation_case_result_id: int | None = None
    orchestration_id: int | None = None
    verdict: str
    corrected_decision: str
    actor: str
    note: str
    created_at: datetime


class DecisionFeedbackSummaryResponse(BaseModel):
    total: int
    accepted: int
    rejected: int
    corrected: int
    acceptance_rate: float
    correction_rate: float
    reviewed_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    recent: list[DecisionFeedbackRead] = Field(default_factory=list)


class PilotMeasurementCreate(BaseModel):
    subject: str = Field(default="demo-user", max_length=120)
    team_subject: str = Field(default="demo-team", max_length=120)
    metric: Literal["review_minutes", "audit_minutes", "release_lead_time_minutes", "incidents", "rollback_minutes"]
    phase: Literal["baseline", "pilot"]
    value: float = Field(ge=0)
    unit: Literal["minutes", "count"]
    sample_size: int = Field(default=1, ge=1, le=10000)
    source: str = Field(default="observed", max_length=64)
    notes: str = Field(default="", max_length=2000)
    measured_at: datetime | None = None


class PilotMeasurementRead(BaseModel):
    id: int
    subject: str
    team_subject: str
    metric: str
    phase: str
    value: float
    unit: str
    sample_size: int
    source: str
    notes: str
    measured_at: datetime
    created_at: datetime


class PilotMetricComparison(BaseModel):
    metric: str
    unit: str
    baseline_value: float | None = None
    pilot_value: float | None = None
    absolute_change: float | None = None
    improvement_rate: float | None = None
    baseline_sample_size: int = 0
    pilot_sample_size: int = 0


class PilotComparisonResponse(BaseModel):
    subject: str | None = None
    team_subject: str | None = None
    source: Literal["measured", "not_configured"]
    metrics: list[PilotMetricComparison] = Field(default_factory=list)
    measured_value_summary: str
    estimated_roi_remains_separate: bool = True


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
