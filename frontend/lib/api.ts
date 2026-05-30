import type {
  DailyContextInput,
  DailyPlanHistoryResponse,
  DailyPlanRecord,
  DailyReflectionHistoryResponse,
  DailyReflectionInput,
  DailyReflectionRecord,
  EntitlementBootstrap,
  HistoryIntegrityResponse,
  CommercialMetricsResponse,
  PilotCloseoutReport,
  PilotReadinessReport,
  PilotScenarioListResponse,
  ReleaseGatePrCiInput,
  MonetizationObservability,
  MonetizationEvent,
  NoteEntry,
  PromptTemplate,
  PromptTemplateImportResponse,
  ReflectionEntry,
  SubscriptionTier,
  SubscriptionLifecycleResponse,
  SubscriptionProfile,
  Task,
  TechnicalAnalysisHistoryResponse,
  TechnicalAnalysisInput,
  TechnicalAnalysisRecord,
  UsageCounter,
  WorkflowOrchestrationHistoryResponse,
  WorkflowOrchestrationMetrics,
  WorkflowOrchestrationRecord,
  WorkflowEvidenceExport,
  WorkflowCheckpointHistoryResponse,
  WorkflowQueueHistoryResponse,
  WorkflowQueueJob,
  WorkflowQueueRunResponse,
  WorkflowStepDefinition,
  WorkflowTemplate,
  WorkflowTemplateImportResponse,
  UserProfile,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const DEFAULT_API_TIMEOUT_MS = 30_000;
const LONG_API_TIMEOUT_MS = 60_000;
const GET_RETRY_DELAY_MS = 250;

type ApiRequestOptions = RequestInit & {
  timeoutMs?: number;
  retries?: number;
};

function normalizeErrorMessage(status: number, bodyText: string): string {
  if (status === 404) return "The requested data was not found.";
  if (status === 400 || status === 422) return "Request validation failed. Please review your input.";
  if (status >= 500) return "Service is temporarily unavailable. Please try again shortly.";

  const trimmed = bodyText.trim();
  if (!trimmed) return "Request failed.";

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail.trim();
    }
    if (
      parsed.detail &&
      typeof parsed.detail === "object" &&
      "message" in parsed.detail &&
      typeof parsed.detail.message === "string" &&
      parsed.detail.message.trim()
    ) {
      return parsed.detail.message.trim();
    }
  } catch {
    return "Request failed.";
  }

  return "Request failed.";
}

function isRetryableRequestFailure(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return error.name === "AbortError" || error.message === "Failed to fetch" || error.message === "NetworkError";
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function request<T>(path: string, init?: ApiRequestOptions): Promise<T> {
  const { timeoutMs = DEFAULT_API_TIMEOUT_MS, retries: explicitRetries, ...fetchInit } = init ?? {};
  const method = (fetchInit.method ?? "GET").toString().toUpperCase();
  const retries = explicitRetries ?? (method === "GET" ? 1 : 0);
  let attempt = 0;

  while (true) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`${API_BASE}${path}`, {
        ...fetchInit,
        headers: {
          "Content-Type": "application/json",
          ...(fetchInit.headers ?? {}),
        },
        cache: "no-store",
        signal: controller.signal,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(normalizeErrorMessage(response.status, message));
      }

      return (await response.json()) as T;
    } catch (error) {
      if (attempt < retries && isRetryableRequestFailure(error)) {
        attempt += 1;
        window.clearTimeout(timeoutId);
        await sleep(GET_RETRY_DELAY_MS * attempt);
        continue;
      }
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error("Request timed out. Please retry.");
      }
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Request failed.");
    } finally {
      window.clearTimeout(timeoutId);
    }
  }
}

export const apiClient = {
  createProfile(payload: {
    name: string;
    role: string;
    language: string;
    preferences: Record<string, unknown>;
    goals: string[];
  }) {
    return request<UserProfile>("/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  generateDailyPlan(payload: DailyContextInput) {
    return request<DailyPlanRecord>("/plans/daily", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listDailyPlans() {
    return request<DailyPlanHistoryResponse>("/plans/history");
  },

  generateDailyReflection(payload: DailyReflectionInput) {
    return request<DailyReflectionRecord>("/reflections/daily", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listDailyReflections() {
    return request<DailyReflectionHistoryResponse>("/reflections/history");
  },

  generateTechnicalAnalysis(payload: TechnicalAnalysisInput) {
    return request<TechnicalAnalysisRecord>("/analysis/technical", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listTechnicalAnalyses() {
    return request<TechnicalAnalysisHistoryResponse>("/analysis/history");
  },

  createReflection(payload: {
    entry_date: string;
    summary: string;
    patterns: string;
    next_actions: string;
    mood: string;
  }) {
    return request<ReflectionEntry>("/reflections", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listTasks() {
    return request<Task[]>("/tasks");
  },

  listReflections() {
    return request<ReflectionEntry[]>("/reflections");
  },

  createKnowledgeEntry(payload: { title: string; content: string; tags: string[] }) {
    return request<NoteEntry>("/knowledge", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listKnowledgeEntries(params?: { q?: string; tag?: string }) {
    const search = new URLSearchParams();
    if (params?.q) search.set("q", params.q);
    if (params?.tag) search.set("tag", params.tag);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<NoteEntry[]>(`/knowledge${suffix}`);
  },

  updateKnowledgeEntry(
    noteId: number,
    payload: {
      title?: string;
      content?: string;
      tags?: string[];
    }
  ) {
    return request<NoteEntry>(`/knowledge/${noteId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  createPromptTemplate(payload: {
    name: string;
    description: string;
    body: string;
    tags: string[];
  }) {
    return request<PromptTemplate>("/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listPromptTemplates(params?: { q?: string; tag?: string }) {
    const search = new URLSearchParams();
    if (params?.q) search.set("q", params.q);
    if (params?.tag) search.set("tag", params.tag);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<PromptTemplate[]>(`/templates${suffix}`);
  },

  updatePromptTemplate(
    templateId: number,
    payload: {
      name?: string;
      description?: string;
      body?: string;
      tags?: string[];
    }
  ) {
    return request<PromptTemplate>(`/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  importBuiltinPromptTemplatesJson(options?: { upsert_by_name?: boolean }) {
    return request<PromptTemplateImportResponse>("/templates/import/json", {
      method: "POST",
      body: JSON.stringify({
        use_builtin: true,
        upsert_by_name: options?.upsert_by_name ?? true,
      }),
    });
  },

  importBuiltinPromptTemplatesSql(options?: { reset_existing?: boolean }) {
    return request<PromptTemplateImportResponse>("/templates/import/sql", {
      method: "POST",
      body: JSON.stringify({
        use_builtin: true,
        reset_existing: options?.reset_existing ?? false,
      }),
    });
  },

  runWorkflowOrchestration(
    payload: {
      entry_source: string;
      pilot_scenario_id?: string;
      team_subject?: string;
      requested_by?: string;
      approval_actor?: string;
      approval_note?: string;
      template_id?: number;
      steps?: WorkflowStepDefinition[];
      daily_context?: DailyContextInput;
      technical_input?: TechnicalAnalysisInput;
      reflection_input?: DailyReflectionInput;
      release_gate_input?: ReleaseGatePrCiInput;
      persist_knowledge?: boolean;
      persist_template?: boolean;
      approval_confirmed?: boolean;
    },
    options?: { subscription_tier?: "free" | "pro" | "power"; entitlement_token?: string }
  ) {
    const headers: Record<string, string> = {};
    if (options?.subscription_tier) headers["X-Subscription-Tier"] = options.subscription_tier;
    if (options?.entitlement_token) headers["X-Entitlement"] = options.entitlement_token;
    return request<WorkflowOrchestrationRecord>("/orchestrations/run", {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      timeoutMs: LONG_API_TIMEOUT_MS,
    });
  },

  enqueueWorkflowOrchestration(
    payload: {
      entry_source: string;
      pilot_scenario_id?: string;
      team_subject?: string;
      requested_by?: string;
      approval_actor?: string;
      approval_note?: string;
      template_id?: number;
      steps?: WorkflowStepDefinition[];
      daily_context?: DailyContextInput;
      technical_input?: TechnicalAnalysisInput;
      reflection_input?: DailyReflectionInput;
      release_gate_input?: ReleaseGatePrCiInput;
      persist_knowledge?: boolean;
      persist_template?: boolean;
      approval_confirmed?: boolean;
    },
    options?: { subscription_tier?: "free" | "pro" | "power"; entitlement_token?: string }
  ) {
    const headers: Record<string, string> = {};
    if (options?.subscription_tier) headers["X-Subscription-Tier"] = options.subscription_tier;
    if (options?.entitlement_token) headers["X-Entitlement"] = options.entitlement_token;
    return request<WorkflowQueueRunResponse>("/orchestrations/queue/run", {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      timeoutMs: LONG_API_TIMEOUT_MS,
    });
  },

  getWorkflowQueueJob(jobId: number) {
    return request<WorkflowQueueJob>(`/orchestrations/queue/${jobId}`, { timeoutMs: LONG_API_TIMEOUT_MS });
  },

  listWorkflowQueueJobs(params?: { status?: string; team_subject?: string; limit?: number }) {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.team_subject) search.set("team_subject", params.team_subject);
    if (params?.limit) search.set("limit", String(params.limit));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowQueueHistoryResponse>(`/orchestrations/queue/history${suffix}`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  retryWorkflowQueueJob(jobId: number, options?: { actor?: string }) {
    const search = new URLSearchParams();
    if (options?.actor) search.set("actor", options.actor);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowQueueRunResponse>(`/orchestrations/queue/${jobId}/retry${suffix}`, {
      method: "POST",
    });
  },

  cancelWorkflowQueueJob(jobId: number, options?: { actor?: string }) {
    const search = new URLSearchParams();
    if (options?.actor) search.set("actor", options.actor);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowQueueJob>(`/orchestrations/queue/${jobId}/cancel${suffix}`, {
      method: "POST",
    });
  },

  listWorkflowOrchestrations(params?: {
    status?: string;
    subscription_tier?: string;
    team_subject?: string;
    limit?: number;
    include_steps?: boolean;
    include_integrity?: boolean;
  }) {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.subscription_tier) search.set("subscription_tier", params.subscription_tier);
    if (params?.team_subject) search.set("team_subject", params.team_subject);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.include_steps !== undefined) search.set("include_steps", String(params.include_steps));
    if (params?.include_integrity !== undefined) search.set("include_integrity", String(params.include_integrity));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowOrchestrationHistoryResponse>(`/orchestrations/history${suffix}`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  getWorkflowOrchestration(orchestrationId: number) {
    return request<WorkflowOrchestrationRecord>(`/orchestrations/${orchestrationId}`, { timeoutMs: LONG_API_TIMEOUT_MS });
  },

  getWorkflowOrchestrationHistoryEvents(orchestrationId: number) {
    return request<HistoryIntegrityResponse>(`/orchestrations/${orchestrationId}/history-events`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  getWorkflowOrchestrationCheckpoints(orchestrationId: number) {
    return request<WorkflowCheckpointHistoryResponse>(`/orchestrations/${orchestrationId}/checkpoints`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  getWorkflowEvidenceExport(orchestrationId: number) {
    return request<WorkflowEvidenceExport>(`/orchestrations/${orchestrationId}/evidence`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  getWorkflowOrchestrationMetrics(days = 7) {
    return request<WorkflowOrchestrationMetrics>(`/orchestrations/metrics?days=${days}`);
  },

  listPilotScenarios() {
    return request<PilotScenarioListResponse>("/orchestrations/pilot-scenarios", {
      retries: 2,
    });
  },

  getEntitlementBootstrapToken() {
    return request<EntitlementBootstrap>("/orchestrations/entitlement/bootstrap", { retries: 1 });
  },

  getSubscriptionEntitlement(subject: string) {
    const search = new URLSearchParams({ subject });
    return request<EntitlementBootstrap>(`/monetization/entitlement?${search.toString()}`, { retries: 1 });
  },

  getMonetizationObservability(days = 7) {
    return request<MonetizationObservability>(`/observability/monetization?days=${days}`);
  },

  getSubscriptionProfile(subject: string) {
    const search = new URLSearchParams({ subject });
    return request<{ profile: SubscriptionProfile | null }>(`/monetization/profile?${search.toString()}`);
  },

  listUsageCounters(subject: string) {
    const search = new URLSearchParams({ subject });
    return request<{ counters: UsageCounter[] }>(`/monetization/usage?${search.toString()}`);
  },

  listMonetizationEvents(limit = 50, subject?: string) {
    const search = new URLSearchParams({ limit: String(limit) });
    if (subject?.trim()) {
      search.set("subject", subject.trim());
    }
    return request<{ events: MonetizationEvent[] }>(`/monetization/events?${search.toString()}`);
  },

  getCommercialMetrics(days = 7, subject?: string) {
    const search = new URLSearchParams({ days: String(days) });
    if (subject?.trim()) {
      search.set("subject", subject.trim());
    }
    return request<CommercialMetricsResponse>(`/monetization/commercial-metrics?${search.toString()}`, {
      retries: 2,
    });
  },

  getPilotReadinessReport(days = 7, subject?: string, teamSubject?: string) {
    const search = new URLSearchParams({ days: String(days) });
    if (subject?.trim()) {
      search.set("subject", subject.trim());
    }
    if (teamSubject?.trim()) {
      search.set("team_subject", teamSubject.trim());
    }
    return request<PilotReadinessReport>(`/monetization/pilot-report?${search.toString()}`, {
      retries: 2,
    });
  },

  getPilotCloseoutReport(days = 7, subject?: string, teamSubject?: string) {
    const search = new URLSearchParams({ days: String(days) });
    if (subject?.trim()) {
      search.set("subject", subject.trim());
    }
    if (teamSubject?.trim()) {
      search.set("team_subject", teamSubject.trim());
    }
    return request<PilotCloseoutReport>(`/monetization/pilot-closeout?${search.toString()}`, {
      retries: 2,
    });
  },

  startManualCheckout(payload: { subject: string; target_tier: SubscriptionTier }) {
    return request<SubscriptionLifecycleResponse>("/monetization/checkout/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  cancelSubscription(subject: string) {
    return request<SubscriptionLifecycleResponse>("/monetization/cancel", {
      method: "POST",
      body: JSON.stringify({ subject }),
    });
  },

  reactivateSubscription(subject: string) {
    return request<SubscriptionLifecycleResponse>("/monetization/reactivate", {
      method: "POST",
      body: JSON.stringify({ subject }),
    });
  },

  createWorkflowTemplate(payload: {
    name: string;
    description: string;
    steps: WorkflowStepDefinition[];
    tags: string[];
    policy?: WorkflowTemplate["policy"];
    enabled?: boolean;
  }) {
    return request<WorkflowTemplate>("/orchestrations/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listWorkflowTemplates(params?: { enabled?: boolean }) {
    const search = new URLSearchParams();
    if (params?.enabled !== undefined) search.set("enabled", String(params.enabled));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowTemplate[]>(`/orchestrations/templates${suffix}`, {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  exportWorkflowTemplates() {
    return request<WorkflowTemplate[]>("/orchestrations/templates/export", {
      timeoutMs: LONG_API_TIMEOUT_MS,
      retries: 2,
    });
  },

  importBuiltinWorkflowTemplates() {
    return request<WorkflowTemplateImportResponse>("/orchestrations/templates/import/builtin", {
      method: "POST",
    });
  },

  importWorkflowTemplates(payload: { items: Omit<WorkflowTemplate, "id" | "created_at" | "updated_at">[] }) {
    return request<WorkflowTemplateImportResponse>("/orchestrations/templates/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
