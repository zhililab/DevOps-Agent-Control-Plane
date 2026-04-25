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
  enabled: boolean;
  created_at: string;
  updated_at: string;
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

export type WorkflowOrchestrationRecord = {
  id: number;
  status: WorkflowOrchestrationStatus;
  duration_ms: number;
  entry_source: string;
  subscription_tier: SubscriptionTier;
  summary: WorkflowOrchestrationSummary;
  steps: WorkflowStepRun[];
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
  error_message: string;
  created_at: string;
  updated_at: string;
  events?: WorkflowQueueJobEvent[];
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
