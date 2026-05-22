"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type {
  SubscriptionTier,
  WorkflowOrchestrationRecord,
  WorkflowQueueJob,
  WorkflowStepDefinition,
  WorkflowTemplate,
  WorkflowTemplatePolicy,
} from "@/lib/types";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

const DEFAULT_STEPS: WorkflowStepDefinition[] = [
  { step_name: "Plan The Day", agent_type: "planner", enabled: true },
  { step_name: "Analyze Technical Signals", agent_type: "analyzer", enabled: true },
  { step_name: "Review And Reflect", agent_type: "reviewer", enabled: true },
];
const DEFAULT_PUBLIC_ENTITLEMENT_TOKEN = process.env.NEXT_PUBLIC_DEFAULT_ENTITLEMENT_TOKEN ?? "";
const ENTITLEMENT_TOKEN_STORAGE_KEY = "entitlement_token";
const BILLING_SUBJECT_STORAGE_KEY = "billing_subject";
const DEFAULT_BILLING_SUBJECT = "demo-user";
const REFRESHABLE_ENTITLEMENT_ERRORS = new Set([
  "missing entitlement token.",
  "invalid entitlement signature.",
  "entitlement token expired.",
  "malformed entitlement token.",
  "malformed entitlement payload.",
  "entitlement tier is missing.",
]);
const WORKFLOW_TEMPLATE_PATTERN_LABELS = {
  sequential: "Sequential",
  concurrent: "Concurrent",
  "maker-checker": "Maker-checker",
  handoff: "Handoff",
  "magentic-ready": "Magentic-ready",
  custom: "Custom",
} as const;
const TEMPLATE_RISK_OPTIONS: WorkflowTemplatePolicy["risk_level"][] = ["low", "medium", "high", "critical"];
const TEMPLATE_TIER_OPTIONS: SubscriptionTier[] = ["free", "pro", "power"];
const TIER_RANK: Record<SubscriptionTier, number> = { free: 0, pro: 1, power: 2 };
const DEFAULT_TEMPLATE_POLICY: WorkflowTemplatePolicy = {
  required_tier: "pro",
  risk_level: "medium",
  approval_required: false,
  allowed_tool_scopes: ["none"],
  billable_work_units: 3,
};

type WorkflowTemplatePattern = keyof typeof WORKFLOW_TEMPLATE_PATTERN_LABELS;

function isWorkflowTemplatePattern(value: string): value is WorkflowTemplatePattern {
  return value in WORKFLOW_TEMPLATE_PATTERN_LABELS;
}

function getWorkflowTemplatePattern(template: Pick<WorkflowTemplate, "tags">): WorkflowTemplatePattern {
  const patternTag = template.tags.find((tag) => tag.toLowerCase().startsWith("pattern:"));
  const pattern = patternTag?.split(":", 2)[1]?.trim().toLowerCase();
  if (pattern && isWorkflowTemplatePattern(pattern)) {
    return pattern;
  }
  return "custom";
}

function formatWorkflowTemplatePattern(template: Pick<WorkflowTemplate, "tags">): string {
  return WORKFLOW_TEMPLATE_PATTERN_LABELS[getWorkflowTemplatePattern(template)];
}

function formatWorkflowTemplateTags(template: Pick<WorkflowTemplate, "tags">): string {
  return template.tags
    .filter((tag) => {
      const normalized = tag.toLowerCase();
      return !(
        normalized.startsWith("pattern:") ||
        normalized.startsWith("tier:") ||
        normalized.startsWith("risk:") ||
        normalized.startsWith("approval:") ||
        normalized.startsWith("tool:") ||
        normalized.startsWith("work-units:")
      );
    })
    .join(", ");
}

function formatWorkflowTemplatePolicy(template: WorkflowTemplate): string {
  return formatTemplatePolicy(template.policy ?? null);
}

function formatTemplatePolicy(policy: WorkflowTemplatePolicy | null): string {
  if (!policy) {
    return "Policy: tier=pro · risk medium · approval optional · work units 1";
  }
  const approval = policy.approval_required ? "approval required" : "approval optional";
  const scopes = policy.allowed_tool_scopes.join(", ");
  return `Policy: tier=${policy.required_tier} · risk ${policy.risk_level} · ${approval} · work units ${policy.billable_work_units} · tools ${scopes}`;
}

function normalizeToolScopes(value: string): string[] {
  const scopes = value
    .split(",")
    .map((scope) => scope.trim().toLowerCase())
    .filter(Boolean);
  return scopes.length > 0 ? Array.from(new Set(scopes)) : ["none"];
}

function normalizeSubscriptionTier(value: unknown): SubscriptionTier | null {
  if (value === "free" || value === "pro" || value === "power") return value;
  return null;
}

function getTemplateRequiredTier(template: WorkflowTemplate | null): SubscriptionTier {
  return template?.policy?.required_tier ?? "pro";
}

function canTierRunTemplate(tier: SubscriptionTier, template: WorkflowTemplate | null): boolean {
  return TIER_RANK[tier] >= TIER_RANK[getTemplateRequiredTier(template)];
}

function decodeEntitlementTier(token: string): SubscriptionTier | null {
  if (typeof window === "undefined") return null;
  const payloadPart = token.trim().split(".", 1)[0];
  if (!payloadPart) return null;
  try {
    const padded = payloadPart + "=".repeat((4 - (payloadPart.length % 4)) % 4);
    const decoded = window.atob(padded.replaceAll("-", "+").replaceAll("_", "/"));
    const payload = JSON.parse(decoded) as { tier?: unknown };
    return normalizeSubscriptionTier(payload.tier);
  } catch {
    return null;
  }
}

function initialStoredValue(key: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  return window.localStorage.getItem(key)?.trim() || fallback;
}

export function OrchestrateView() {
  const [entrySource, setEntrySource] = useState("web_ui");
  const [teamSubject, setTeamSubject] = useState("platform-team");
  const [requestedBy, setRequestedBy] = useState("sre-lead");
  const [approvalActor, setApprovalActor] = useState("release-manager");
  const [approvalNote, setApprovalNote] = useState("Approved for trusted DevOps workflow demo execution.");
  const [runMode, setRunMode] = useState<"sync" | "async">("sync");
  const [billingSubject, setBillingSubject] = useState(() =>
    initialStoredValue(BILLING_SUBJECT_STORAGE_KEY, DEFAULT_BILLING_SUBJECT)
  );
  const [entitlementToken, setEntitlementToken] = useState(() =>
    initialStoredValue(ENTITLEMENT_TOKEN_STORAGE_KEY, DEFAULT_PUBLIC_ENTITLEMENT_TOKEN)
  );
  const [steps, setSteps] = useState<WorkflowStepDefinition[]>(DEFAULT_STEPS);
  const [templateName, setTemplateName] = useState("Default DevOps Loop");
  const [templateDescription, setTemplateDescription] = useState(
    "Plan -> Analyze -> Review deterministic orchestration for daily DevOps execution."
  );
  const [templateTags, setTemplateTags] = useState("orchestration,devops,daily");
  const [templateRequiredTier, setTemplateRequiredTier] = useState<SubscriptionTier>(DEFAULT_TEMPLATE_POLICY.required_tier);
  const [templateRiskLevel, setTemplateRiskLevel] = useState<WorkflowTemplatePolicy["risk_level"]>(
    DEFAULT_TEMPLATE_POLICY.risk_level
  );
  const [templateApprovalRequired, setTemplateApprovalRequired] = useState(DEFAULT_TEMPLATE_POLICY.approval_required);
  const [templateToolScopes, setTemplateToolScopes] = useState(DEFAULT_TEMPLATE_POLICY.allowed_tool_scopes.join(","));
  const [templateBillableWorkUnits, setTemplateBillableWorkUnits] = useState(String(DEFAULT_TEMPLATE_POLICY.billable_work_units));
  const [templateEnabled, setTemplateEnabled] = useState(true);

  const [tasksText, setTasksText] = useState("Stabilize release pipeline\nPrepare deployment checklist");
  const [meetingsText, setMeetingsText] = useState("10:30 Platform sync");
  const [blockersText, setBlockersText] = useState("Waiting for approval from infra");
  const [prioritiesText, setPrioritiesText] = useState("Stabilize release pipeline");

  const [issueDescription, setIssueDescription] = useState(
    "Deployment stage intermittently fails after artifact upload."
  );
  const [errorsText, setErrorsText] = useState("TimeoutError: upstream did not respond");
  const [logsText, setLogsText] = useState("stage: upload\nregistry call timeout\njob failed");
  const [codeSnippetsText, setCodeSnippetsText] = useState("curl --max-time 30 https://registry/upload");

  const [completedText, setCompletedText] = useState("Triaged incident timeline");
  const [unfinishedText, setUnfinishedText] = useState("Verify registry retries in staging");
  const [reflectionBlockersText, setReflectionBlockersText] = useState("Missing owner for validation");
  const [moodNotes, setMoodNotes] = useState("Steady focus, but context switching after meetings.");

  const [persistKnowledge, setPersistKnowledge] = useState(true);
  const [persistTemplate, setPersistTemplate] = useState(false);
  const [approvalConfirmed, setApprovalConfirmed] = useState(false);

  const [latest, setLatest] = useState<WorkflowOrchestrationRecord | null>(null);
  const [queueJob, setQueueJob] = useState<WorkflowQueueJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);

  useEffect(() => {
    void loadTemplates();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const cachedSubject = window.localStorage.getItem(BILLING_SUBJECT_STORAGE_KEY)?.trim() || DEFAULT_BILLING_SUBJECT;
    setBillingSubject(cachedSubject);
    const cached = window.localStorage.getItem(ENTITLEMENT_TOKEN_STORAGE_KEY)?.trim();
    if (cached) {
      setEntitlementToken(cached);
    } else if (DEFAULT_PUBLIC_ENTITLEMENT_TOKEN.trim()) {
      rememberEntitlementToken(DEFAULT_PUBLIC_ENTITLEMENT_TOKEN);
    }
    void (async () => {
      const subscriptionToken = await tryLoadSubscriptionEntitlement(cachedSubject, { showStatus: false });
      if (!subscriptionToken) {
        await tryBootstrapEntitlementToken({ showStatus: false });
      }
    })();
  }, []);

  useEffect(() => {
    if (!queueJob || queueJob.status === "succeeded" || queueJob.status === "failed" || queueJob.status === "canceled") {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshQueueJob(queueJob.id, false);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [queueJob]);

  const activeStepCount = useMemo(() => steps.filter((step) => step.enabled).length, [steps]);
  const selectedWorkflowTemplate = useMemo(
    () => templates.find((template) => String(template.id) === selectedTemplateId) ?? null,
    [selectedTemplateId, templates]
  );
  const activeEntitlementTier = useMemo(() => decodeEntitlementTier(entitlementToken), [entitlementToken]);
  const compatibleTemplate = useMemo(() => {
    if (!activeEntitlementTier) return null;
    return templates.find((template) => template.enabled && canTierRunTemplate(activeEntitlementTier, template)) ?? null;
  }, [activeEntitlementTier, templates]);
  const selectedTemplateRequiresUpgrade = Boolean(
    selectedWorkflowTemplate && activeEntitlementTier && !canTierRunTemplate(activeEntitlementTier, selectedWorkflowTemplate)
  );
  const currentTemplatePolicy = useMemo<WorkflowTemplatePolicy>(
    () => ({
      required_tier: templateRequiredTier,
      risk_level: templateRiskLevel,
      approval_required: templateApprovalRequired,
      allowed_tool_scopes: normalizeToolScopes(templateToolScopes),
      billable_work_units: Math.max(1, Math.min(100, Number.parseInt(templateBillableWorkUnits, 10) || activeStepCount || 1)),
    }),
    [activeStepCount, templateApprovalRequired, templateBillableWorkUnits, templateRequiredTier, templateRiskLevel, templateToolScopes]
  );

  function buildPayload() {
    const payload: {
      entry_source: string;
      team_subject: string;
      requested_by: string;
      approval_actor: string;
      approval_note: string;
      template_id?: number;
      steps: WorkflowStepDefinition[];
      daily_context: {
        tasks: string[];
        meetings: string[];
        blockers: string[];
        priorities: string[];
      };
      technical_input: {
        issue_description: string;
        errors: string[];
        logs: string;
        code_snippets: string[];
      };
      reflection_input: {
        completed: string[];
        unfinished: string[];
        blockers: string[];
        mood_or_notes: string;
      };
      persist_knowledge: boolean;
      persist_template: boolean;
      approval_confirmed: boolean;
    } = {
      entry_source: entrySource.trim() || "web_ui",
      team_subject: teamSubject.trim() || "platform-team",
      requested_by: requestedBy.trim() || "sre-lead",
      approval_actor: approvalActor.trim(),
      approval_note: approvalNote.trim(),
      steps,
      daily_context: {
        tasks: splitLines(tasksText),
        meetings: splitLines(meetingsText),
        blockers: splitLines(blockersText),
        priorities: splitLines(prioritiesText),
      },
      technical_input: {
        issue_description: issueDescription.trim(),
        errors: splitLines(errorsText),
        logs: logsText.trim(),
        code_snippets: splitLines(codeSnippetsText),
      },
      reflection_input: {
        completed: splitLines(completedText),
        unfinished: splitLines(unfinishedText),
        blockers: splitLines(reflectionBlockersText),
        mood_or_notes: moodNotes.trim(),
      },
      persist_knowledge: persistKnowledge,
      persist_template: persistTemplate,
      approval_confirmed: approvalConfirmed,
    };
    if (selectedTemplateId) {
      payload.template_id = Number(selectedTemplateId);
    }
    return payload;
  }

  function buildRunOptions() {
    const options: { entitlement_token?: string } = {};
    if (entitlementToken.trim()) {
      options.entitlement_token = entitlementToken.trim();
    }
    return options;
  }

  function rememberEntitlementToken(token: string) {
    const trimmed = token.trim();
    setEntitlementToken(trimmed);
    if (typeof window === "undefined") return;
    if (trimmed) {
      window.localStorage.setItem(ENTITLEMENT_TOKEN_STORAGE_KEY, trimmed);
    } else {
      window.localStorage.removeItem(ENTITLEMENT_TOKEN_STORAGE_KEY);
    }
  }

  function rememberBillingSubject(subject: string) {
    const normalized = subject.trim() || DEFAULT_BILLING_SUBJECT;
    setBillingSubject(normalized);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(BILLING_SUBJECT_STORAGE_KEY, normalized);
    }
    return normalized;
  }

  function forgetEntitlementToken() {
    setEntitlementToken("");
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(ENTITLEMENT_TOKEN_STORAGE_KEY);
    }
  }

  function isRefreshableEntitlementError(value: unknown): boolean {
    if (!(value instanceof Error)) return false;
    return REFRESHABLE_ENTITLEMENT_ERRORS.has(value.message.trim().toLowerCase());
  }

  async function tryBootstrapEntitlementToken(options: { showStatus?: boolean } = {}): Promise<string | null> {
    try {
      const response = await apiClient.getEntitlementBootstrapToken();
      const token = response.token.trim();
      if (!token) return null;
      rememberEntitlementToken(token);
      if (options.showStatus) {
        setStatus("Loaded entitlement token from server bootstrap endpoint.");
      }
      return token;
    } catch {
      return null;
    }
  }

  async function tryLoadSubscriptionEntitlement(
    subject = billingSubject,
    options: { showStatus?: boolean } = {}
  ): Promise<string | null> {
    try {
      const normalizedSubject = rememberBillingSubject(subject);
      const response = await apiClient.getSubscriptionEntitlement(normalizedSubject);
      const token = typeof response.token === "string" ? response.token.trim() : "";
      if (!token) return null;
      rememberEntitlementToken(token);
      if (options.showStatus) {
        setStatus(`${normalizedSubject} ${response.tier.toUpperCase()} subscription entitlement loaded.`);
      }
      return token;
    } catch (loadError) {
      if (options.showStatus) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load subscription entitlement.");
      }
      return null;
    }
  }

  async function refreshQueueJob(jobId: number, showToast = true) {
    try {
      const current = await apiClient.getWorkflowQueueJob(jobId);
      setQueueJob(current);
      if (current.status === "succeeded" && current.orchestration_id) {
        const detail = await apiClient.getWorkflowOrchestration(current.orchestration_id);
        setLatest(detail);
      }
      if (showToast) {
        setStatus(`Queue job #${jobId} status: ${current.status}.`);
      }
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh queue status.");
    }
  }

  async function loadTemplates() {
    try {
      const response = await apiClient.listWorkflowTemplates();
      setTemplates(response);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load workflow templates.");
    } finally {
      setIsLoadingTemplates(false);
    }
  }

  async function onRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);
    if (selectedTemplateRequiresUpgrade && activeEntitlementTier && selectedWorkflowTemplate) {
      setError(
        `Current ${activeEntitlementTier.toUpperCase()} entitlement cannot run '${selectedWorkflowTemplate.name}'. ` +
          `This template requires ${getTemplateRequiredTier(selectedWorkflowTemplate).toUpperCase()}.`
      );
      return;
    }
    setIsSubmitting(true);
    setQueueJob(null);

    try {
      rememberEntitlementToken(entitlementToken);
      const executeRun = async (options: { entitlement_token?: string }) => {
        if (runMode === "sync") {
          const record = await apiClient.runWorkflowOrchestration(buildPayload(), options);
          setLatest(record);
          setStatus(`Orchestration #${record.id} completed with status: ${record.status}.`);
          return;
        }

        const queued = await apiClient.enqueueWorkflowOrchestration(buildPayload(), options);
        setQueueJob({
          id: queued.job_id,
          status: queued.status,
          attempts: queued.attempts,
          max_attempts: queued.max_attempts,
          cancel_requested: false,
          orchestration_id: null,
          team_subject: teamSubject.trim() || "platform-team",
          requested_by: requestedBy.trim() || "sre-lead",
          approval_actor: approvalActor.trim(),
          approval_note: approvalNote.trim(),
          error_message: "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        setStatus(`Queue job #${queued.job_id} submitted.`);
        await refreshQueueJob(queued.job_id, false);
      };

      const runOptions = buildRunOptions();
      try {
        await executeRun(runOptions);
      } catch (runError) {
        if (!isRefreshableEntitlementError(runError)) {
          throw runError;
        }
        forgetEntitlementToken();
        const bootstrapToken = await tryBootstrapEntitlementToken({ showStatus: false });
        if (!bootstrapToken) {
          throw runError;
        }
        await executeRun({
          ...runOptions,
          entitlement_token: bootstrapToken,
        });
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Failed to run orchestration.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onRetryQueueJob() {
    if (!queueJob) return;
    setStatus(null);
    setError(null);
    try {
      const retried = await apiClient.retryWorkflowQueueJob(queueJob.id, { actor: requestedBy.trim() || "sre-lead" });
      setQueueJob((current) =>
        current
          ? {
              ...current,
              status: retried.status,
              attempts: retried.attempts,
              max_attempts: retried.max_attempts,
              error_message: "",
            }
          : null
      );
      setStatus(`Queue job #${queueJob.id} retried.`);
      await refreshQueueJob(queueJob.id, false);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Failed to retry queue job.");
    }
  }

  async function onCancelQueueJob() {
    if (!queueJob) return;
    setStatus(null);
    setError(null);
    try {
      const canceled = await apiClient.cancelWorkflowQueueJob(queueJob.id, { actor: requestedBy.trim() || "sre-lead" });
      setQueueJob(canceled);
      setStatus(`Queue job #${queueJob.id} cancel request accepted.`);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Failed to cancel queue job.");
    }
  }

  async function onSaveTemplate() {
    setStatus(null);
    setError(null);
    try {
      const created = await apiClient.createWorkflowTemplate({
        name: templateName.trim(),
        description: templateDescription.trim(),
        steps,
        tags: splitLines(templateTags.replaceAll(",", "\n")),
        policy: currentTemplatePolicy,
        enabled: templateEnabled,
      });
      setTemplates((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setStatus(`Template '${created.name}' saved.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save template.");
    }
  }

  async function onExportTemplates() {
    setStatus(null);
    setError(null);
    try {
      const exported = await apiClient.exportWorkflowTemplates();
      setStatus(`Exported ${exported.length} workflow templates.`);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Failed to export templates.");
    }
  }

  async function onImportTemplates() {
    setStatus(null);
    setError(null);
    try {
      const response = await apiClient.importWorkflowTemplates({
        items: templates.map((template) => ({
          name: template.name,
          description: template.description,
          steps: template.steps,
          tags: template.tags,
          policy: template.policy,
          enabled: template.enabled,
        })),
      });
      setStatus(`Import finished: imported=${response.imported}, updated=${response.updated}.`);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import templates.");
    }
  }

  async function onImportBuiltinTemplates() {
    setStatus(null);
    setError(null);
    setIsLoadingTemplates(true);
    try {
      const response = await apiClient.importBuiltinWorkflowTemplates();
      await loadTemplates();
      setStatus(`Curated templates imported: imported=${response.imported}, updated=${response.updated}.`);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import curated templates.");
      setIsLoadingTemplates(false);
    }
  }

  function applyTemplate(templateId: string) {
    setSelectedTemplateId(templateId);
    setApprovalConfirmed(false);
    if (!templateId) return;
    const id = Number(templateId);
    const matched = templates.find((template) => template.id === id);
    if (!matched) return;
    setSteps(matched.steps);
    setTemplateName(matched.name);
    setTemplateDescription(matched.description);
    setTemplateTags(formatWorkflowTemplateTags(matched));
    const policy = matched.policy ?? DEFAULT_TEMPLATE_POLICY;
    setTemplateRequiredTier(policy.required_tier);
    setTemplateRiskLevel(policy.risk_level);
    setTemplateApprovalRequired(policy.approval_required);
    setTemplateToolScopes(policy.allowed_tool_scopes.join(","));
    setTemplateBillableWorkUnits(String(policy.billable_work_units));
    setTemplateEnabled(matched.enabled);
  }

  return (
    <PageCard
      title="Workflow Orchestrator"
      description="Run deterministic DevOps workflows with signed entitlement, policy checks, and replayable output."
    >
      <section className="result-block">
        <h3>Orchestration Controls</h3>
        <label>
          Entry Source
          <input value={entrySource} onChange={(event) => setEntrySource(event.target.value)} />
        </label>
        <div className="trust-grid">
          <label>
            Team
            <input value={teamSubject} onChange={(event) => setTeamSubject(event.target.value)} />
          </label>
          <label>
            Requester
            <input value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} />
          </label>
          <label>
            Approver
            <input value={approvalActor} onChange={(event) => setApprovalActor(event.target.value)} />
          </label>
          <label>
            Approval Note
            <input value={approvalNote} onChange={(event) => setApprovalNote(event.target.value)} />
          </label>
        </div>
        <label>
          Run Mode
          <select value={runMode} onChange={(event) => setRunMode(event.target.value as "sync" | "async")}>
            <option value="sync">Sync (blocking)</option>
            <option value="async">Async Queue</option>
          </select>
        </label>
        <label>
          Billing Subject
          <input value={billingSubject} onChange={(event) => setBillingSubject(event.target.value)} />
        </label>
        <div className="button-row compact-controls">
          <button
            type="button"
            onClick={() => {
              setStatus(null);
              setError(null);
              void tryLoadSubscriptionEntitlement(billingSubject, { showStatus: true });
            }}
          >
            Load Subscription Entitlement
          </button>
          <p className="muted">
            Current entitlement: {activeEntitlementTier ? activeEntitlementTier.toUpperCase() : "Unknown"} · account{" "}
            {billingSubject.trim() || DEFAULT_BILLING_SUBJECT}
          </p>
        </div>
        <label>
          Entitlement Token (signed)
          <input
            value={entitlementToken}
            onChange={(event) => setEntitlementToken(event.target.value)}
            placeholder="Auto-fetched on demand when server bootstrap is enabled"
          />
        </label>
        <p className="muted">Active steps: {activeStepCount}. Free tier allows a single active step.</p>
      </section>

      <section className="result-grid">
        {steps.map((step, index) => (
          <article key={`${step.agent_type}-${index}`} className="result-block">
            <h4>{step.step_name}</h4>
            <p className="muted">Agent: {step.agent_type}</p>
            <label>
              Enabled
              <input
                type="checkbox"
                checked={step.enabled}
                onChange={(event) => {
                  setSteps((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, enabled: event.target.checked } : item
                    )
                  );
                }}
              />
            </label>
          </article>
        ))}
      </section>

      <section className="result-block">
        <h3>Workflow Templates</h3>
        <p className="muted">Save current step configuration as reusable orchestration template.</p>
        <label>
          Apply Existing Template
          <select value={selectedTemplateId} onChange={(event) => applyTemplate(event.target.value)}>
            <option value="">Select template</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </label>
        {selectedWorkflowTemplate ? (
          <>
            <p className="muted">
              Pattern: {formatWorkflowTemplatePattern(selectedWorkflowTemplate)}
              {formatWorkflowTemplateTags(selectedWorkflowTemplate)
                ? ` · Tags: ${formatWorkflowTemplateTags(selectedWorkflowTemplate)}`
                : ""}
            </p>
            <p className="muted">{formatWorkflowTemplatePolicy(selectedWorkflowTemplate)}</p>
            {selectedWorkflowTemplate.policy?.approval_required ? (
              <label>
                Human Approval Confirmed
                <input
                  type="checkbox"
                  checked={approvalConfirmed}
                  onChange={(event) => setApprovalConfirmed(event.target.checked)}
                />
              </label>
            ) : null}
            {selectedTemplateRequiresUpgrade && activeEntitlementTier ? (
              <div className="status status-warning">
                <p>
                  Current {activeEntitlementTier.toUpperCase()} entitlement cannot run this template. It requires{" "}
                  {getTemplateRequiredTier(selectedWorkflowTemplate).toUpperCase()}.
                </p>
                {compatibleTemplate ? (
                  <button type="button" onClick={() => applyTemplate(String(compatibleTemplate.id))}>
                    Use {activeEntitlementTier.toUpperCase()}-compatible template
                  </button>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}
        <label>
          Template Name
          <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
        </label>
        <label>
          Template Description
          <textarea value={templateDescription} rows={3} onChange={(event) => setTemplateDescription(event.target.value)} />
        </label>
        <label>
          Template Tags (comma separated)
          <input value={templateTags} onChange={(event) => setTemplateTags(event.target.value)} />
        </label>
        <section className="policy-authoring-panel" aria-label="template-policy-controls">
          <div>
            <p className="eyebrow">Template Policy</p>
            <h4>Commercial Gate</h4>
            <p className="muted">{formatTemplatePolicy(currentTemplatePolicy)}</p>
          </div>
          <div className="trust-grid">
            <label>
              Required Tier
              <select
                value={templateRequiredTier}
                onChange={(event) => setTemplateRequiredTier(event.target.value as SubscriptionTier)}
              >
                {TEMPLATE_TIER_OPTIONS.map((tier) => (
                  <option key={tier} value={tier}>
                    {tier}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Risk Level
              <select
                value={templateRiskLevel}
                onChange={(event) => setTemplateRiskLevel(event.target.value as WorkflowTemplatePolicy["risk_level"])}
              >
                {TEMPLATE_RISK_OPTIONS.map((risk) => (
                  <option key={risk} value={risk}>
                    {risk}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Billable Work Units
              <input
                type="number"
                min={1}
                max={100}
                value={templateBillableWorkUnits}
                onChange={(event) => setTemplateBillableWorkUnits(event.target.value)}
              />
            </label>
            <label>
              Allowed Tool Scopes
              <input value={templateToolScopes} onChange={(event) => setTemplateToolScopes(event.target.value)} />
            </label>
          </div>
          <div className="button-row compact-controls">
            <label>
              Approval Required
              <input
                type="checkbox"
                checked={templateApprovalRequired}
                onChange={(event) => setTemplateApprovalRequired(event.target.checked)}
              />
            </label>
            <label>
              Template Enabled
              <input
                type="checkbox"
                checked={templateEnabled}
                onChange={(event) => setTemplateEnabled(event.target.checked)}
              />
            </label>
          </div>
        </section>
        <div className="button-row">
          <button type="button" onClick={onSaveTemplate}>
            Save Template
          </button>
          <button type="button" onClick={onExportTemplates}>
            Export Templates
          </button>
          <button type="button" onClick={onImportTemplates}>
            Import Templates
          </button>
          <button type="button" onClick={onImportBuiltinTemplates}>
            Import Curated Templates
          </button>
        </div>
        {isLoadingTemplates ? <p className="muted">Loading templates...</p> : null}
      </section>

      <form onSubmit={onRun}>
        <h3>Planner Input</h3>
        <label>
          Tasks (one per line)
          <textarea value={tasksText} rows={3} onChange={(event) => setTasksText(event.target.value)} />
        </label>
        <label>
          Meetings (one per line)
          <textarea value={meetingsText} rows={2} onChange={(event) => setMeetingsText(event.target.value)} />
        </label>
        <label>
          Blockers (one per line)
          <textarea value={blockersText} rows={2} onChange={(event) => setBlockersText(event.target.value)} />
        </label>
        <label>
          Priorities (one per line)
          <textarea value={prioritiesText} rows={2} onChange={(event) => setPrioritiesText(event.target.value)} />
        </label>

        <h3>Analyzer Input</h3>
        <label>
          Issue Description
          <textarea value={issueDescription} rows={3} onChange={(event) => setIssueDescription(event.target.value)} />
        </label>
        <label>
          Errors (one per line)
          <textarea value={errorsText} rows={2} onChange={(event) => setErrorsText(event.target.value)} />
        </label>
        <label>
          Logs
          <textarea value={logsText} rows={3} onChange={(event) => setLogsText(event.target.value)} />
        </label>
        <label>
          Code Snippets (one per line)
          <textarea value={codeSnippetsText} rows={2} onChange={(event) => setCodeSnippetsText(event.target.value)} />
        </label>

        <h3>Reviewer Input</h3>
        <label>
          Completed (one per line)
          <textarea value={completedText} rows={2} onChange={(event) => setCompletedText(event.target.value)} />
        </label>
        <label>
          Unfinished (one per line)
          <textarea value={unfinishedText} rows={2} onChange={(event) => setUnfinishedText(event.target.value)} />
        </label>
        <label>
          Blockers (one per line)
          <textarea
            value={reflectionBlockersText}
            rows={2}
            onChange={(event) => setReflectionBlockersText(event.target.value)}
          />
        </label>
        <label>
          Mood Or Notes
          <textarea value={moodNotes} rows={3} onChange={(event) => setMoodNotes(event.target.value)} />
        </label>

        <label>
          Persist To Knowledge
          <input
            type="checkbox"
            checked={persistKnowledge}
            onChange={(event) => setPersistKnowledge(event.target.checked)}
          />
        </label>
        <label>
          Persist Replay Prompt Template
          <input
            type="checkbox"
            checked={persistTemplate}
            onChange={(event) => setPersistTemplate(event.target.checked)}
          />
        </label>
        <button type="submit" disabled={isSubmitting || selectedTemplateRequiresUpgrade}>
          {isSubmitting ? "Submitting..." : runMode === "sync" ? "Run Orchestration" : "Enqueue Orchestration"}
        </button>
      </form>

      {status ? <p className="status status-success">{status}</p> : null}
      {error ? <p className="status status-error">{error}</p> : null}
      {latest || queueJob ? (
        <p>
          <Link href="/orchestrations">View Orchestration History</Link>
        </p>
      ) : null}

      {queueJob ? (
        <section className="reflection-section">
          <h3>Queue Job</h3>
          <article className="result-block">
            <p>
              <strong>Job #{queueJob.id}</strong> · status={queueJob.status} · attempts={queueJob.attempts}/
              {queueJob.max_attempts}
            </p>
            <p className="muted">
              Team {queueJob.team_subject || "unassigned"} · requested by {queueJob.requested_by || "unknown"}
              {queueJob.approval_actor ? ` · approved by ${queueJob.approval_actor}` : ""}
            </p>
            {queueJob.orchestration_id ? <p className="muted">Orchestration #{queueJob.orchestration_id} attached.</p> : null}
            {queueJob.error_message ? <p className="muted">Error: {queueJob.error_message}</p> : null}
            <div className="button-row">
              <button type="button" onClick={() => void refreshQueueJob(queueJob.id)}>
                Refresh Status
              </button>
              <button type="button" onClick={onRetryQueueJob} disabled={queueJob.status !== "failed" && queueJob.status !== "canceled"}>
                Retry
              </button>
              <button type="button" onClick={onCancelQueueJob} disabled={queueJob.status === "succeeded" || queueJob.status === "failed" || queueJob.status === "canceled"}>
                Cancel
              </button>
            </div>
          </article>
        </section>
      ) : null}

      {latest ? (
        <section className="reflection-section">
          <h3>Run Replay</h3>
          <article className="result-block">
            <p>
              <strong>Run #{latest.id}</strong> · status={latest.status} · tier={latest.subscription_tier} ·
              duration={latest.duration_ms}ms
            </p>
            <p className="muted">
              Team {latest.team_subject || "unassigned"} · requested by {latest.requested_by || "unknown"}
              {latest.approval_actor ? ` · approved by ${latest.approval_actor}` : ""} · checkpoints{" "}
              {latest.checkpoint_count}
            </p>
            <p>{latest.summary.conclusion}</p>
          </article>
          <div className="result-grid">
            {latest.steps.map((step) => (
              <article key={step.id} className="result-block">
                <h4>
                  {step.step_name} ({step.agent_type}) - {step.status}
                </h4>
                <p>{step.audit.conclusion}</p>
                <p className="muted">Evidence: {step.audit.evidence}</p>
                <p className="muted">Risk: {step.audit.risk}</p>
                <p className="muted">Next: {step.audit.next_action}</p>
                {step.fallback_action ? <p className="muted">Fallback: {step.fallback_action}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </PageCard>
  );
}
