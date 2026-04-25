"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type { WorkflowOrchestrationRecord, WorkflowQueueJob, WorkflowStepDefinition, WorkflowTemplate } from "@/lib/types";

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

export function OrchestrateView() {
  const [entrySource, setEntrySource] = useState("web_ui");
  const [runMode, setRunMode] = useState<"sync" | "async">("sync");
  const [subscriptionTier, setSubscriptionTier] = useState<"free" | "pro" | "power">("pro");
  const [entitlementToken, setEntitlementToken] = useState(DEFAULT_PUBLIC_ENTITLEMENT_TOKEN);
  const [steps, setSteps] = useState<WorkflowStepDefinition[]>(DEFAULT_STEPS);
  const [templateName, setTemplateName] = useState("Default DevOps Loop");
  const [templateDescription, setTemplateDescription] = useState(
    "Plan -> Analyze -> Review deterministic orchestration for daily DevOps execution."
  );
  const [templateTags, setTemplateTags] = useState("orchestration,devops,daily");

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

  const [latest, setLatest] = useState<WorkflowOrchestrationRecord | null>(null);
  const [queueJob, setQueueJob] = useState<WorkflowQueueJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);

  useEffect(() => {
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

    void loadTemplates();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const cached = window.localStorage.getItem("entitlement_token");
    if (cached) {
      setEntitlementToken(cached);
      return;
    }
    if (DEFAULT_PUBLIC_ENTITLEMENT_TOKEN.trim()) {
      window.localStorage.setItem("entitlement_token", DEFAULT_PUBLIC_ENTITLEMENT_TOKEN.trim());
    }
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

  function buildPayload() {
    return {
      entry_source: entrySource.trim() || "web_ui",
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
    };
  }

  function buildRunOptions() {
    const options: { subscription_tier?: "free" | "pro" | "power"; entitlement_token?: string } = {
      subscription_tier: subscriptionTier,
    };
    if (entitlementToken.trim()) {
      options.entitlement_token = entitlementToken.trim();
    }
    return options;
  }

  function isMissingEntitlementError(value: unknown): boolean {
    if (!(value instanceof Error)) return false;
    return value.message.trim().toLowerCase() === "missing entitlement token.";
  }

  async function tryBootstrapEntitlementToken(): Promise<string | null> {
    try {
      const response = await apiClient.getEntitlementBootstrapToken();
      const token = response.token.trim();
      if (!token) return null;
      setEntitlementToken(token);
      if (typeof window !== "undefined") {
        window.localStorage.setItem("entitlement_token", token);
      }
      setStatus("Loaded entitlement token from server bootstrap endpoint.");
      return token;
    } catch {
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

  async function onRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);
    setIsSubmitting(true);
    setQueueJob(null);

    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem("entitlement_token", entitlementToken.trim());
      }
      const executeRun = async (options: { subscription_tier?: "free" | "pro" | "power"; entitlement_token?: string }) => {
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
        if (!isMissingEntitlementError(runError)) {
          throw runError;
        }
        const bootstrapToken = await tryBootstrapEntitlementToken();
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
      const retried = await apiClient.retryWorkflowQueueJob(queueJob.id);
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
      const canceled = await apiClient.cancelWorkflowQueueJob(queueJob.id);
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
        enabled: true,
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
          enabled: template.enabled,
        })),
      });
      setStatus(`Import finished: imported=${response.imported}, updated=${response.updated}.`);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import templates.");
    }
  }

  function applyTemplate(templateId: string) {
    const id = Number(templateId);
    const matched = templates.find((template) => template.id === id);
    if (!matched) return;
    setSteps(matched.steps);
    setTemplateName(matched.name);
    setTemplateDescription(matched.description);
    setTemplateTags(matched.tags.join(","));
  }

  return (
    <PageCard
      title="Workflow Orchestrator"
      description="Run deterministic multi-agent orchestration across planning, analysis, and reflection."
    >
      <section className="result-block">
        <h3>Orchestration Controls</h3>
        <label>
          Entry Source
          <input value={entrySource} onChange={(event) => setEntrySource(event.target.value)} />
        </label>
        <label>
          Subscription Tier
          <select value={subscriptionTier} onChange={(event) => setSubscriptionTier(event.target.value as "free" | "pro" | "power")}>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
            <option value="power">Power</option>
          </select>
        </label>
        <label>
          Run Mode
          <select value={runMode} onChange={(event) => setRunMode(event.target.value as "sync" | "async")}>
            <option value="sync">Sync (blocking)</option>
            <option value="async">Async Queue</option>
          </select>
        </label>
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
          <select defaultValue="" onChange={(event) => applyTemplate(event.target.value)}>
            <option value="">Select template</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </label>
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
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : runMode === "sync" ? "Run Orchestration" : "Enqueue Orchestration"}
        </button>
      </form>

      {status ? <p className="status status-success">{status}</p> : null}
      {error ? <p className="status status-error">{error}</p> : null}

      {queueJob ? (
        <section className="reflection-section">
          <h3>Queue Job</h3>
          <article className="result-block">
            <p>
              <strong>Job #{queueJob.id}</strong> · status={queueJob.status} · attempts={queueJob.attempts}/
              {queueJob.max_attempts}
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
