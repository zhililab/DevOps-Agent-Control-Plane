export type UserProfile = {
  id: number;
  name: string;
  role: string;
  language: string;
  preferences: Record<string, unknown>;
  goals: string[];
  created_at: string;
  updated_at: string;
};

export type Task = {
  id: number;
  title: string;
  domain: string;
  status: string;
  priority: number;
  source: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReflectionEntry = {
  id: number;
  entry_date: string;
  summary: string;
  patterns: string;
  next_actions: string;
  mood: string;
  created_at: string;
  updated_at: string;
};

export type DailyReflectionInput = {
  completed: string[];
  unfinished: string[];
  blockers: string[];
  mood_or_notes: string;
};

export type DailyReflectionSummary = {
  day_summary: string;
  unfinished_items: string[];
  pattern_hints: string[];
  tomorrow_suggestions: string[];
};

export type DailyReflectionRecord = {
  id: number;
  entry_date: string;
  input: DailyReflectionInput;
  summary: DailyReflectionSummary;
  created_at: string;
  record_source: string;
  business_timezone: string;
};

export type DailyReflectionHistoryResponse = {
  items: DailyReflectionRecord[];
};

export type DailyContextInput = {
  tasks: string[];
  meetings: string[];
  blockers: string[];
  priorities: string[];
};

export type DailyPlanStructured = {
  top_priorities: string[];
  recommended_order: string[];
  risks_and_reminders: string[];
  next_actions: string[];
  status_summary: string;
};

export type DailyPlanRecord = {
  id: number;
  plan_date: string;
  context: DailyContextInput;
  plan: DailyPlanStructured;
  created_at: string;
  record_source: string;
  business_timezone: string;
};

export type DailyPlanHistoryResponse = {
  items: DailyPlanRecord[];
};

export type TechnicalAnalysisInput = {
  logs: string;
  errors: string[];
  code_snippets: string[];
  issue_description: string;
};

export type ReleaseGatePrCiInput = {
  pr_url: string;
  pr_diff_summary: string;
  ci_log_summary: string;
  target_environment: string;
  change_risk: string;
};

export type StructuredAnalysisResult = {
  problem_statement: string;
  likely_causes: string[];
  validation_steps: string[];
  fix_options: string[];
  risks: string[];
  follow_up_tasks: string[];
};

export type TechnicalAnalysisOutput = StructuredAnalysisResult;

export type TechnicalAnalysisRecord = {
  id: number;
  analysis_date: string;
  input: TechnicalAnalysisInput;
  output: TechnicalAnalysisOutput;
  created_at: string;
  record_source: string;
  business_timezone: string;
};

export type TechnicalAnalysisHistoryResponse = {
  items: TechnicalAnalysisRecord[];
};

export type NoteEntry = {
  id: number;
  title: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type PromptTemplate = {
  id: number;
  name: string;
  description: string;
  body: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type PromptTemplateImportResponse = {
  mode: string;
  imported: number;
  updated: number;
  skipped: number;
  total: number;
};

export type WorkflowAgentType = "planner" | "analyzer" | "reviewer";
export type WorkflowStepStatus = "success" | "failed" | "skipped";
export type WorkflowOrchestrationStatus = "running" | "success" | "partial_success" | "failed" | "canceled";
export type SubscriptionTier = "free" | "pro" | "power";

export type WorkflowStepDefinition = {
  step_name: string;
  agent_type: WorkflowAgentType;
  enabled: boolean;
};

export type WorkflowTemplate = {
  id: number;
  name: string;
  description: string;
  steps: WorkflowStepDefinition[];
  tags: string[];
  policy?: WorkflowTemplatePolicy | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkflowTemplatePolicy = {
  required_tier: SubscriptionTier;
  risk_level: "low" | "medium" | "high" | "critical";
  approval_required: boolean;
  allowed_tool_scopes: string[];
  billable_work_units: number;
};

export type WorkflowAuditBlock = {
  conclusion: string;
  evidence: string;
  risk: string;
  next_action: string;
};

export type WorkflowStepRun = {
  id: number;
  step_name: string;
  agent_type: WorkflowAgentType;
  status: WorkflowStepStatus;
  input_summary: string;
  output_summary: string;
  audit: WorkflowAuditBlock;
  fallback_action: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
};

export type WorkflowOrchestrationSummary = {
  conclusion: string;
  risks: string[];
  next_actions: string[];
};

export type WorkflowRunPolicyGate = {
  template_id: number | null;
  template_name: string;
  required_tier: SubscriptionTier;
  risk_level: "low" | "medium" | "high" | "critical";
  approval_required: boolean;
  approval_confirmed: boolean;
  allowed_tool_scopes: string[];
  billable_work_units: number;
  decision: "approve" | "block" | "needs human review" | string;
};

export type WorkflowRoiEvidence = {
  review_time_saved_minutes: number;
  audit_time_saved_minutes: number;
  blocked_risk_count: number;
  blocked_risk_value_usd: number;
  estimated_customer_value_usd: number;
  billable_work_units: number;
  assumptions: string[];
};

export type WorkflowOrchestrationRecord = {
  id: number;
  status: WorkflowOrchestrationStatus;
  duration_ms: number;
  entry_source: string;
  pilot_scenario_id?: string | null;
  subscription_tier: SubscriptionTier;
  team_subject: string;
  requested_by: string;
  approval_actor: string;
  approval_note: string;
  policy_gate?: WorkflowRunPolicyGate | null;
  billable_work_units?: number;
  roi_evidence?: WorkflowRoiEvidence | null;
  summary: WorkflowOrchestrationSummary;
  steps: WorkflowStepRun[];
  ledger_integrity?: HistoryIntegritySummary | null;
  checkpoint_count: number;
  created_at: string;
  updated_at: string;
};

export type WorkflowOrchestrationHistoryResponse = {
  items: WorkflowOrchestrationRecord[];
};

export type WorkflowOrchestrationMetrics = {
  period_days: number;
  total_runs: number;
  weekly_active_orchestrations: number;
  partial_success_rate: number;
  average_duration_ms: number;
  billable_work_units: number;
  successful_audited_workflows: number;
  approval_required_blocks: number;
  template_policy_upgrade_blocks: number;
  approved_runs: number;
  checkpointed_runs: number;
  failed_jobs_needing_owner: number;
};

export type HistoryEvent = {
  id: number;
  event_uid: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  event_version: number;
  source_table: string;
  source_id: string;
  correlation_id: string;
  payload: Record<string, unknown>;
  payload_sha256: string;
  previous_event_sha256: string;
  occurred_at: string;
  created_at: string;
  integrity_status: "valid" | "invalid" | string;
  integrity_error: string;
};

export type HistoryIntegrityResponse = {
  entity_type: string;
  entity_id: string;
  integrity_status: "valid" | "invalid" | string;
  event_count: number;
  events: HistoryEvent[];
};

export type HistoryIntegritySummary = Omit<HistoryIntegrityResponse, "events">;

export type WorkflowCheckpoint = {
  id: number;
  checkpoint_uid: string;
  entity_type: string;
  entity_id: string;
  orchestration_id: number | null;
  queue_job_id: number | null;
  checkpoint_type: string;
  step_name: string;
  step_index: number | null;
  status: string;
  payload: Record<string, unknown>;
  payload_sha256: string;
  created_by: string;
  created_at: string;
  integrity_status: "valid" | "invalid" | string;
  integrity_error: string;
};

export type WorkflowCheckpointHistoryResponse = {
  items: WorkflowCheckpoint[];
};

export type EntitlementBootstrap = {
  token: string;
  tier: SubscriptionTier;
  expires_at: string;
};

export type MonetizationHealthStatus = "healthy" | "warning" | "critical";

export type MonetizationObservabilityKpis = {
  total_revenue_usd: number;
  paid_runs: number;
  conversion_rate: number;
  failed_payment_rate: number;
};

export type MonetizationObservabilityTrendPoint = {
  date: string;
  revenue_usd: number;
  paid_runs: number;
  conversion_rate: number;
};

export type MonetizationObservabilityHealth = {
  status: MonetizationHealthStatus;
  summary: string;
  incidents: string[];
};

export type MonetizationObservability = {
  period_days: number;
  kpis: MonetizationObservabilityKpis;
  trend: MonetizationObservabilityTrendPoint[];
  health: MonetizationObservabilityHealth;
};

export type MonetizationSubscriptionStatus = "inactive" | "active" | "past_due" | "canceled";
export type UsageMetric = "workflow_runs" | "queued_runs";

export type SubscriptionProfile = {
  id: number;
  subject: string;
  tier: SubscriptionTier;
  status: MonetizationSubscriptionStatus;
  billing_provider: string;
  external_customer_id: string;
  external_subscription_id: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  entitlements: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type UsageCounter = {
  id: number;
  subscription_profile_id: number;
  metric: UsageMetric;
  period_start: string;
  period_end: string;
  used: number;
  limit: number;
  created_at: string;
  updated_at: string;
};

export type MonetizationEvent = {
  id: number;
  subscription_profile_id: number | null;
  usage_counter_id: number | null;
  event_kind: string;
  event: Record<string, unknown>;
  created_at: string;
};

export type CommercialMetricsResponse = {
  window_days: number;
  generated_at: string;
  subject: string | null;
  subscription_summary: {
    active_subjects: number;
    profile_count: number;
    tier_distribution: Record<SubscriptionTier, number>;
    status_distribution: Record<MonetizationSubscriptionStatus, number>;
  };
  usage_summary: {
    workflow_runs_used: number;
    workflow_runs_limit: number;
    queued_runs_used: number;
    queued_runs_limit: number;
    usage_subjects: number;
  };
  plan_usage: {
    workflow_runs_used: number;
    workflow_runs_limit: number;
    queued_runs_used: number;
    queued_runs_limit: number;
    period_start: string | null;
    period_end: string | null;
  };
  commercial_events: Array<{
    action: string;
    count: number;
  }>;
  policy_blocks: {
    approval_required: number;
    upgrade_required: number;
    quota_exceeded: number;
    total: number;
  };
  billable_work_units: {
    total: number;
    audited_workflows: number;
    average_per_run: number;
  };
  roi_summary: {
    runs_with_roi: number;
    estimated_customer_value_usd: number;
    review_time_saved_minutes: number;
    audit_time_saved_minutes: number;
    blocked_risk_count: number;
    blocked_risk_value_usd: number;
    billable_work_units: number;
    work_units_by_template: Array<{
      template_id: number | null;
      template_name: string;
      runs: number;
      billable_work_units: number;
      estimated_customer_value_usd: number;
    }>;
  };
  top_templates: Array<{
    template_id: number | null;
    template_name: string;
    runs: number;
    billable_work_units: number;
    required_tier: SubscriptionTier;
    risk_level: WorkflowTemplatePolicy["risk_level"];
    approval_required: boolean;
  }>;
  trend: Array<{
    date: string;
    billable_work_units: number;
    audited_workflows: number;
    policy_blocks: number;
  }>;
  anomaly_hints: Array<{
    code: string;
    severity: "info" | "warning" | "critical";
    message: string;
  }>;
};

export type WorkflowEvidenceExport = {
  orchestration_id: number;
  generated_at: string;
  format: "markdown";
  markdown: string;
  data: Record<string, unknown>;
};

export type SubscriptionLifecycleResponse = {
  profile: SubscriptionProfile;
  counters: UsageCounter[];
  event: MonetizationEvent;
};

export type WorkflowQueueJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

export type WorkflowQueueRunResponse = {
  job_id: number;
  status: WorkflowQueueJobStatus;
  attempts: number;
  max_attempts: number;
};

export type WorkflowQueueJobEvent = {
  id: number;
  queue_job_id: number;
  event_type: string;
  status: WorkflowQueueJobStatus;
  detail: string;
  created_at: string;
};

export type WorkflowQueueJob = {
  id: number;
  status: WorkflowQueueJobStatus;
  attempts: number;
  max_attempts: number;
  cancel_requested: boolean;
  orchestration_id: number | null;
  team_subject: string;
  requested_by: string;
  approval_actor: string;
  approval_note: string;
  error_message: string;
  created_at: string;
  updated_at: string;
  events?: WorkflowQueueJobEvent[];
  checkpoints?: WorkflowCheckpoint[];
};

export type WorkflowQueueHistoryResponse = {
  items: WorkflowQueueJob[];
};

export type WorkflowTemplateImportResponse = {
  imported: number;
  updated: number;
  skipped: number;
  total: number;
};

export type PilotScenario = {
  id: string;
  name: string;
  description: string;
  expected_gate_behavior: "approve" | "block" | "needs human review";
  required_tier: SubscriptionTier;
  approval_required: boolean;
  approval_confirmed: boolean;
  recommended_template_name: string;
  release_gate_input: ReleaseGatePrCiInput;
  daily_context: DailyContextInput;
  technical_input: TechnicalAnalysisInput;
  reflection_input: DailyReflectionInput;
  success_signal: string;
};

export type PilotScenarioListResponse = {
  items: PilotScenario[];
};

export type PilotReadinessReport = {
  window_days: number;
  generated_at: string;
  subject: string | null;
  team_subject: string | null;
  status: "ready" | "needs evidence" | "needs approval metadata";
  runs_completed: number;
  evidence_exportable_runs: number;
  ledger_valid_runs: number;
  checkpointed_runs: number;
  approval_required_runs: number;
  blocked_or_needs_review_runs: number;
  estimated_value_usd: number;
  review_time_saved_minutes: number;
  audit_time_saved_minutes: number;
  metadata_completeness: number;
  missing_metadata_runs: number;
  scenario_statuses: PilotScenarioCompletion[];
  power_upgrade_evidence: PilotPowerUpgradeEvidence;
  success_criteria: string[];
  recommendations: string[];
};

export type PilotScenarioCompletion = {
  id: string;
  name: string;
  status: "missing" | "needs evidence" | "completed";
  expected_gate_behavior: "approve" | "block" | "needs human review";
  required_tier: SubscriptionTier;
  completed_runs: number;
  evidence_exportable_runs: number;
  ledger_valid_runs: number;
  checkpointed_runs: number;
  approval_metadata_complete: boolean;
  latest_orchestration_id: number | null;
};

export type PilotPowerUpgradeEvidence = {
  power_required_runs: number;
  approval_required_runs: number;
  blocked_or_needs_review_runs: number;
  evidence_exportable_runs: number;
  ledger_valid_runs: number;
  estimated_value_usd: number;
  review_audit_time_saved_minutes: number;
  recommendation: string;
};

export type PilotCloseoutReport = {
  window_days: number;
  generated_at: string;
  subject: string | null;
  team_subject: string | null;
  status: "ready" | "needs evidence" | "needs approval metadata";
  markdown: string;
  data: Record<string, unknown>;
};
