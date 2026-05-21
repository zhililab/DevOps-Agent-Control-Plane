"use client";

import { useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { buildQueueTimelineReplay } from "@/features/orchestrations/queueTimeline";
import { apiClient } from "@/lib/api";
import type { WorkflowOrchestrationRecord, WorkflowQueueJob, WorkflowQueueJobStatus } from "@/lib/types";

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export function OrchestrationsHistoryView() {
  const [items, setItems] = useState<WorkflowOrchestrationRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "success" | "partial_success" | "failed" | "canceled">("all");
  const [tierFilter, setTierFilter] = useState<"all" | "free" | "pro" | "power">("all");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [queueJobs, setQueueJobs] = useState<WorkflowQueueJob[]>([]);
  const [queueStatusFilter, setQueueStatusFilter] = useState<"all" | WorkflowQueueJobStatus>("all");
  const [selectedQueueJobId, setSelectedQueueJobId] = useState<number | null>(null);
  const [selectedQueueJob, setSelectedQueueJob] = useState<WorkflowQueueJob | null>(null);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueActionMessage, setQueueActionMessage] = useState<string | null>(null);
  const [activeQueueActionJobId, setActiveQueueActionJobId] = useState<number | null>(null);
  const [isLoadingQueue, setIsLoadingQueue] = useState(true);
  const [isLoadingQueueDetail, setIsLoadingQueueDetail] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiClient.listWorkflowOrchestrations({
          status: statusFilter === "all" ? undefined : statusFilter,
          subscription_tier: tierFilter === "all" ? undefined : tierFilter,
          limit: 50,
        });
        setItems(Array.isArray(response.items) ? response.items : []);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load orchestration history.");
      } finally {
        setIsLoading(false);
      }
    }

    setIsLoading(true);
    void load();
  }, [statusFilter, tierFilter]);

  useEffect(() => {
    async function loadQueueJobs() {
      try {
        const response = await apiClient.listWorkflowQueueJobs({
          status: queueStatusFilter === "all" ? undefined : queueStatusFilter,
          limit: 50,
        });
        const nextJobs = Array.isArray(response.items) ? response.items : [];
        setQueueJobs(nextJobs);
        setQueueError(null);

        if (nextJobs.length === 0) {
          setSelectedQueueJobId(null);
          setSelectedQueueJob(null);
          return;
        }

        setSelectedQueueJobId((current) => {
          if (current && nextJobs.some((job) => job.id === current)) return current;
          return nextJobs[0].id;
        });
      } catch (loadError) {
        setQueueError(loadError instanceof Error ? loadError.message : "Failed to load queue jobs.");
      } finally {
        setIsLoadingQueue(false);
      }
    }

    setIsLoadingQueue(true);
    void loadQueueJobs();
  }, [queueStatusFilter]);

  useEffect(() => {
    const jobId = selectedQueueJobId;
    if (jobId === null) return;
    const resolvedJobId: number = jobId;

    async function loadQueueJobDetail() {
      try {
        setIsLoadingQueueDetail(true);
        const detail = await apiClient.getWorkflowQueueJob(resolvedJobId);
        setSelectedQueueJob(detail);
        setQueueError(null);
      } catch (loadError) {
        setQueueError(loadError instanceof Error ? loadError.message : "Failed to load queue job detail.");
      } finally {
        setIsLoadingQueueDetail(false);
      }
    }

    void loadQueueJobDetail();
  }, [selectedQueueJobId]);

  const timeline = selectedQueueJob ? buildQueueTimelineReplay(selectedQueueJob) : null;

  async function refreshQueueJobDetail(jobId: number) {
    const detail = await apiClient.getWorkflowQueueJob(jobId);
    setSelectedQueueJob(detail);
    setQueueJobs((current) => current.map((item) => (item.id === detail.id ? detail : item)));
    return detail;
  }

  async function onRetryQueueJob(job: WorkflowQueueJob) {
    setQueueError(null);
    setQueueActionMessage(null);
    setActiveQueueActionJobId(job.id);
    try {
      const retried = await apiClient.retryWorkflowQueueJob(job.id);
      setQueueJobs((current) =>
        current.map((item) =>
          item.id === job.id
            ? {
                ...item,
                status: retried.status,
                attempts: retried.attempts,
                max_attempts: retried.max_attempts,
                cancel_requested: false,
                error_message: "",
              }
            : item
        )
      );
      setSelectedQueueJobId(job.id);
      setQueueActionMessage(`Queue job #${job.id} retry requested.`);
      await refreshQueueJobDetail(job.id);
    } catch (retryError) {
      setQueueError(retryError instanceof Error ? retryError.message : "Failed to retry queue job.");
    } finally {
      setActiveQueueActionJobId(null);
    }
  }

  async function onCancelQueueJob(job: WorkflowQueueJob) {
    setQueueError(null);
    setQueueActionMessage(null);
    setActiveQueueActionJobId(job.id);
    try {
      const canceled = await apiClient.cancelWorkflowQueueJob(job.id);
      setQueueJobs((current) => current.map((item) => (item.id === canceled.id ? canceled : item)));
      setSelectedQueueJobId(job.id);
      setSelectedQueueJob(canceled);
      setQueueActionMessage(`Queue job #${job.id} cancel request accepted.`);
    } catch (cancelError) {
      setQueueError(cancelError instanceof Error ? cancelError.message : "Failed to cancel queue job.");
    } finally {
      setActiveQueueActionJobId(null);
    }
  }

  return (
    <PageCard title="Orchestration History" description="Filter, review, and audit multi-agent orchestration runs.">
      <section className="result-block">
        <h3>Filters</h3>
        <label>
          Status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
            <option value="all">All</option>
            <option value="running">Running</option>
            <option value="success">Success</option>
            <option value="partial_success">Partial Success</option>
            <option value="failed">Failed</option>
            <option value="canceled">Canceled</option>
          </select>
        </label>
        <label>
          Tier
          <select value={tierFilter} onChange={(event) => setTierFilter(event.target.value as typeof tierFilter)}>
            <option value="all">All</option>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
            <option value="power">Power</option>
          </select>
        </label>
      </section>

      {error ? <p className="status status-error">{error}</p> : null}
      {isLoading ? <p className="muted">Loading orchestration history...</p> : null}
      {!isLoading && items.length === 0 ? <p className="muted">No orchestration runs found.</p> : null}

      {items.map((item) => (
        <section key={item.id} id={`orchestration-run-${item.id}`} className="history-plan">
          <h3>
            Run #{item.id} · {item.status} · {item.subscription_tier}
          </h3>
          <p>{item.summary.conclusion}</p>
          <p className="muted">Duration: {item.duration_ms}ms | Source: {item.entry_source}</p>

          <div className="result-grid">
            {item.steps.map((step) => (
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
      ))}

      <section className="result-block">
        <h3>Queue Job List</h3>
        <label>
          Queue Status
          <select
            value={queueStatusFilter}
            onChange={(event) => setQueueStatusFilter(event.target.value as typeof queueStatusFilter)}
          >
            <option value="all">All</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="canceled">Canceled</option>
          </select>
        </label>
        {queueError ? <p className="status status-error">{queueError}</p> : null}
        {queueActionMessage ? <p className="status status-success">{queueActionMessage}</p> : null}
        {isLoadingQueue ? <p className="muted">Loading queue jobs...</p> : null}
        {!isLoadingQueue && queueJobs.length === 0 ? <p className="muted">No queue jobs found.</p> : null}

        {queueJobs.map((job) => (
          <article key={job.id} className="result-block">
            <p>
              <strong>Job #{job.id}</strong> · status={job.status} · attempts={job.attempts}/{job.max_attempts}
            </p>
            <p className="muted">cancel_requested={String(job.cancel_requested)}</p>
            <p className="muted">
              orchestration=
              {job.orchestration_id ? <a href={`#orchestration-run-${job.orchestration_id}`}>Run #{job.orchestration_id}</a> : "none"}
            </p>
            <p className="muted">updated={formatTimestamp(job.updated_at)}</p>
            <div className="button-row">
              <button type="button" onClick={() => setSelectedQueueJobId(job.id)} disabled={selectedQueueJobId === job.id}>
                {selectedQueueJobId === job.id ? "Selected" : "View Timeline Replay"}
              </button>
              <button
                type="button"
                onClick={() => void onRetryQueueJob(job)}
                disabled={
                  activeQueueActionJobId === job.id || (job.status !== "failed" && job.status !== "canceled")
                }
              >
                Retry Job
              </button>
              <button
                type="button"
                onClick={() => void onCancelQueueJob(job)}
                disabled={
                  activeQueueActionJobId === job.id ||
                  job.status === "succeeded" ||
                  job.status === "failed" ||
                  job.status === "canceled"
                }
              >
                Cancel Job
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="result-block">
        <h3>Timeline Replay</h3>
        {!selectedQueueJob ? <p className="muted">Select a queue job to inspect timeline replay.</p> : null}
        {isLoadingQueueDetail ? <p className="muted">Loading selected queue job...</p> : null}
        {selectedQueueJob && timeline ? (
          <>
            <p>
              Job #{selectedQueueJob.id} · latest status={selectedQueueJob.status}
            </p>
            <p className="muted">
              Timeline source:{" "}
              {timeline.mode === "event_log"
                ? "Observed queue events."
                : "Inferred from queue snapshot fields (event log not currently available)."}
            </p>
            <div className="result-grid">
              {timeline.events.map((event) => (
                <article key={event.id} className="result-block">
                  <h4>{event.title}</h4>
                  <p className="muted">
                    {formatTimestamp(event.at)} · {event.source}
                  </p>
                  <p>{event.detail}</p>
                </article>
              ))}
            </div>
          </>
        ) : null}
      </section>
    </PageCard>
  );
}
