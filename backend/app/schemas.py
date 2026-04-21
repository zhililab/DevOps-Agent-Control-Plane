from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    tasks: list[str] = Field(default_factory=list)
    meetings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)


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


class DailyPlanHistoryResponse(BaseModel):
    items: list[DailyPlanSavedResponse]


class DailyReflectionInput(BaseModel):
    completed: list[str] = Field(default_factory=list)
    unfinished: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    mood_or_notes: str = ""


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


class DailyReflectionHistoryResponse(BaseModel):
    items: list[DailyReflectionSavedResponse]


class TechnicalAnalysisInput(BaseModel):
    logs: str = ""
    errors: list[str] = Field(default_factory=list)
    code_snippets: list[str] = Field(default_factory=list)
    issue_description: str = ""

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
