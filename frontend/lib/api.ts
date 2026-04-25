import type {
  DailyContextInput,
  DailyPlanHistoryResponse,
  DailyPlanRecord,
  DailyReflectionHistoryResponse,
  DailyReflectionInput,
  DailyReflectionRecord,
  MonetizationObservability,
  NoteEntry,
  PromptTemplate,
  PromptTemplateImportResponse,
  ReflectionEntry,
  Task,
  TechnicalAnalysisHistoryResponse,
  TechnicalAnalysisInput,
  TechnicalAnalysisRecord,
  WorkflowOrchestrationHistoryResponse,
  WorkflowOrchestrationMetrics,
  WorkflowOrchestrationRecord,
  WorkflowQueueHistoryResponse,
  WorkflowQueueJob,
  WorkflowQueueRunResponse,
  WorkflowStepDefinition,
  WorkflowTemplate,
  WorkflowTemplateImportResponse,
  UserProfile,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const API_TIMEOUT_MS = 10_000;

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
  } catch {
    return "Request failed.";
  }

  return "Request failed.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
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
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Request timed out. Please retry.");
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Request failed.");
  } finally {
    clearTimeout(timeoutId);
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
      steps: WorkflowStepDefinition[];
      daily_context?: DailyContextInput;
      technical_input?: TechnicalAnalysisInput;
      reflection_input?: DailyReflectionInput;
      persist_knowledge?: boolean;
      persist_template?: boolean;
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
    });
  },

  enqueueWorkflowOrchestration(
    payload: {
      entry_source: string;
      steps: WorkflowStepDefinition[];
      daily_context?: DailyContextInput;
      technical_input?: TechnicalAnalysisInput;
      reflection_input?: DailyReflectionInput;
      persist_knowledge?: boolean;
      persist_template?: boolean;
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
    });
  },

  getWorkflowQueueJob(jobId: number) {
    return request<WorkflowQueueJob>(`/orchestrations/queue/${jobId}`);
  },

  listWorkflowQueueJobs(params?: { status?: string; limit?: number }) {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.limit) search.set("limit", String(params.limit));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowQueueHistoryResponse>(`/orchestrations/queue/history${suffix}`);
  },

  retryWorkflowQueueJob(jobId: number) {
    return request<WorkflowQueueRunResponse>(`/orchestrations/queue/${jobId}/retry`, {
      method: "POST",
    });
  },

  cancelWorkflowQueueJob(jobId: number) {
    return request<WorkflowQueueJob>(`/orchestrations/queue/${jobId}/cancel`, {
      method: "POST",
    });
  },

  listWorkflowOrchestrations(params?: { status?: string; subscription_tier?: string; limit?: number }) {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.subscription_tier) search.set("subscription_tier", params.subscription_tier);
    if (params?.limit) search.set("limit", String(params.limit));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<WorkflowOrchestrationHistoryResponse>(`/orchestrations/history${suffix}`);
  },

  getWorkflowOrchestration(orchestrationId: number) {
    return request<WorkflowOrchestrationRecord>(`/orchestrations/${orchestrationId}`);
  },

  getWorkflowOrchestrationMetrics(days = 7) {
    return request<WorkflowOrchestrationMetrics>(`/orchestrations/metrics?days=${days}`);
  },

  getMonetizationObservability(days = 7) {
    return request<MonetizationObservability>(`/orchestrations/monetization/observability?days=${days}`);
  },

  createWorkflowTemplate(payload: {
    name: string;
    description: string;
    steps: WorkflowStepDefinition[];
    tags: string[];
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
    return request<WorkflowTemplate[]>(`/orchestrations/templates${suffix}`);
  },

  exportWorkflowTemplates() {
    return request<WorkflowTemplate[]>("/orchestrations/templates/export");
  },

  importWorkflowTemplates(payload: { items: Omit<WorkflowTemplate, "id" | "created_at" | "updated_at">[] }) {
    return request<WorkflowTemplateImportResponse>("/orchestrations/templates/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
