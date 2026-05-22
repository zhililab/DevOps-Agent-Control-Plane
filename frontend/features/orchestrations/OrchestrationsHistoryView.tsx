"use client";

import { useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { buildQueueTimelineReplay } from "@/features/orchestrations/queueTimeline";
import { apiClient } from "@/lib/api";
import type {
  HistoryIntegrityResponse,
  WorkflowCheckpoint,
  WorkflowOrchestrationRecord,
  WorkflowQueueJob,
  WorkflowQueueJobStatus,
} from "@/lib/types";

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export function OrchestrationsHistoryView() {
  const [items, setItems] = useState<WorkflowOrchestrationRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "success" | "partial_success" | "failed" | "canceled">("all");
  const [tierFilter, setTierFilter] = useState<"all" | "free" | "pro" | "power">("all");
  const [teamFilter, setTeamFilter] = useState("");
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
  const [historyIntegrityByRunId, setHistoryIntegrityByRunId] = useState<Record<number, HistoryIntegrityResponse>>({});
  const [activeHistoryCheckRunId, setActiveHistoryCheckRunId] = useState<number | null>(null);
  const [checkpointsByRunId, setCheckpointsByRunId] = useState<Record<number, WorkflowCheckpoint[]>>({});
  const [activeCheckpointRunId, setActiveCheckpointRunId] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiClient.listWorkflowOrchestrations({
          status: statusFilter === "all" ? undefined : statusFilter,
          subscription_tier: tierFilter === "all" ? undefined : tierFilter,
          team_subject: teamFilter.trim() || undefined,
          limit: 25,
        });
        const nextItems = Array.isArray(response.items) ? response.items : [];
        setItems(nextItems);
        setHistoryIntegrityByRunId((current) => {
          const next = { ...current };
          nextItems.forEach((item) => {
            if (item.ledger_integrity) {
              next[item.id] = { ...item.ledger_integrity, events: current[item.id]?.events ?? [] };
            }
          });
          return next;
        });
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load orchestration history.");
      } finally {
        setIsLoading(false);
      }
    }

    setIsLoading(true);
    void load();
  }, [statusFilter, tierFilter, teamFilter]);

  useEffect(() => {
    async function loadQueueJobs() {
      try {
        const response = await apiClient.listWorkflowQueueJobs({
          status: queueStatusFilter === "all" ? undefined : queueStatusFilter,
          team_subject: teamFilter.trim() || undefined,
          limit: 25,
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
  }, [queueStatusFilter, teamFilter]);

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

  async function onVerifyHistory(runId: number) {
    setError(null);
    setActiveHistoryCheckRunId(runId);
    try {
      const integrity = await apiClient.getWorkflowOrchestrationHistoryEvents(runId);
      const checkpoints = await apiClient.getWorkflowOrchestrationCheckpoints(runId);
      setHistoryIntegrityByRunId((current) => ({
        ...current,
        [runId]: integrity,
      }));
      setCheckpointsByRunId((current) => ({
        ...current,
        [runId]: Array.isArray(checkpoints.items) ? checkpoints.items : [],
      }));
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : "Failed to verify history ledger.");
    } finally {
      setActiveHistoryCheckRunId(null);
    }
  }

  async function onLoadCheckpoints(runId: number) {
    setError(null);
    setActiveCheckpointRunId(runId);
    try {
      const response = await apiClient.getWorkflowOrchestrationCheckpoints(runId);
      setCheckpointsByRunId((current) => ({
        ...current,
        [runId]: Array.isArray(response.items) ? response.items : [],
      }));
    } catch (checkpointError) {
      setError(checkpointError instanceof Error ? checkpointError.message : "Failed to load checkpoints.");
    } finally {
      setActiveCheckpointRunId(null);
    }
  }

  return (
    <PageCard
      title="Orchestration History"
      description="Replay runs, verify ledger integrity, and inspect queue lifecycle."
    >
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
        <label>
          Team
          <input
            value={teamFilter}
            onChange={(event) => setTeamFilter(event.target.value)}
            placeholder="Leave empty to show all teams"
          />
        </label>
      </section>

      {error ? <p className="status status-error">{error}</p> : null}
      {isLoading ? <p className="muted">Loading orchestration history...</p> : null}
      {!isLoading && items.length === 0 ? <p className="muted">No orchestration runs found.</p> : null}

      {items.map((item) => (
        <section key={item.id} id={`orchestration-run-${item.id}`} className="history-plan orchestration-run-card">
          {(() => {
            const integrity = historyIntegrityByRunId[item.id] ?? item.ledger_integrity;
            const checkpoints = checkpointsByRunId[item.id] ?? [];
            return (
              <>
                <div className="ledger-strip">
                  <div className="ledger-badges">
                    <p className={`status ledger-status ${integrity?.integrity_status === "invalid" ? "status-error" : "status-success"}`}>
                      History Ledger:{" "}
                      {integrity
                        ? `${integrity.integrity_status} · ${integrity.event_count} event(s)`
                        : "not checked"}
                    </p>
                    <p className="status status-default">Checkpoints: {checkpoints.length || item.checkpoint_count || 0}</p>
                  </div>
                  <div className="button-row">
                    <button
                      type="button"
                      onClick={() => void onVerifyHistory(item.id)}
                      disabled={activeHistoryCheckRunId === item.id}
                    >
                      {activeHistoryCheckRunId === item.id ? "Checking Ledger..." : "Verify History Ledger"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void onLoadCheckpoints(item.id)}
                      disabled={activeCheckpointRunId === item.id}
                    >
                      {activeCheckpointRunId === item.id ? "Loading Checkpoints..." : "Load Checkpoint Timeline"}
                    </button>
                  </div>
                </div>
                {checkpoints.length > 0 ? (
                  <div className="checkpoint-timeline" aria-label={`checkpoint-timeline-${item.id}`}>
                    {checkpoints.slice(0, 8).map((checkpoint) => (
                      <article key={checkpoint.id} className="checkpoint-node">
                        <p className="eyebrow">{checkpoint.checkpoint_type}</p>
                        <h4>
                          {checkpoint.step_name || checkpoint.entity_type} · {checkpoint.status}
                        </h4>
                        <p className="muted">
                          {formatTimestamp(checkpoint.created_at)} · by {checkpoint.created_by} ·{" "}
                          {checkpoint.integrity_status}
                        </p>
                      </article>
                    ))}
                  </div>
                ) : null}
              </>
            );
          })()}
          <div className="run-heading">
            <div>
              <h3>Run #{item.id}</h3>
              <p>{item.summary.conclusion}</p>
            </div>
            <p className="run-meta">
              {item.status} · {item.subscription_tier} · {item.duration_ms}ms
            </p>
          </div>
          <p className="muted">
            Source: {item.entry_source} · Team: {item.team_subject || "unassigned"} · requested by{" "}
            {item.requested_by || "unknown"}
            {item.approval_actor ? ` · approved by ${item.approval_actor}` : ""}
          </p>
          {item.approval_note ? <p className="muted">Approval note: {item.approval_note}</p> : null}

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
          <article key={job.id} className="result-block queue-job-card">
            <div className="queue-job-header">
              <p>
                <strong>Job #{job.id}</strong>
              </p>
              <p className="run-meta">
                {job.status} · attempts {job.attempts}/{job.max_attempts}
              </p>
            </div>
            <div className="queue-job-meta">
              <p>cancel_requested={String(job.cancel_requested)}</p>
              <p>team={job.team_subject || "unassigned"}</p>
              <p>requester={job.requested_by || "unknown"}</p>
              <p>
                orchestration=
                {job.orchestration_id ? <a href={`#orchestration-run-${job.orchestration_id}`}>Run #{job.orchestration_id}</a> : "none"}
              </p>
              <p>updated={formatTimestamp(job.updated_at)}</p>
            </div>
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
            <div className="queue-job-header">
              <p>
                <strong>Job #{selectedQueueJob.id}</strong>
              </p>
              <p className="run-meta">latest status={selectedQueueJob.status}</p>
            </div>
            <p className="muted">
              Timeline source:{" "}
              {timeline.mode === "event_log"
                ? "Observed queue events."
                : "Inferred from queue snapshot fields (event log not currently available)."}
            </p>
            {selectedQueueJob.checkpoints && selectedQueueJob.checkpoints.length > 0 ? (
              <p className="muted">Checkpoint snapshots: {selectedQueueJob.checkpoints.length}</p>
            ) : null}
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
