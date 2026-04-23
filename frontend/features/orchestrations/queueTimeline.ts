import type { WorkflowQueueJob, WorkflowQueueJobStatus } from "@/lib/types";

export type QueueTimelineEvent = {
  id: string;
  at: string;
  title: string;
  detail: string;
  source: "observed" | "inferred";
};

export type QueueTimelineReplay = {
  mode: "event_log" | "inferred";
  events: QueueTimelineEvent[];
};

type QueueJobWithOptionalEvents = WorkflowQueueJob & {
  events?: Array<{ event?: string; status?: WorkflowQueueJobStatus; at?: string; detail?: string }>;
};

function normalizeTimestamp(value: string | undefined, fallback: string): string {
  if (!value) return fallback;
  return value;
}

function inferredStatusTitle(status: WorkflowQueueJobStatus): string {
  if (status === "queued") return "Job queued";
  if (status === "running") return "Job running";
  if (status === "succeeded") return "Job succeeded";
  if (status === "failed") return "Job failed";
  return "Job canceled";
}

function inferTimeline(job: WorkflowQueueJob): QueueTimelineReplay {
  const events: QueueTimelineEvent[] = [
    {
      id: `inferred-created-${job.id}`,
      at: job.created_at,
      title: "Job created",
      detail: "Inferred from queue snapshot. Initial state assumed queued unless a later status is present.",
      source: "inferred",
    },
    {
      id: `inferred-status-${job.id}`,
      at: job.updated_at,
      title: inferredStatusTitle(job.status),
      detail: `Inferred latest status=${job.status}.`,
      source: "inferred",
    },
  ];

  if (job.attempts > 0) {
    events.push({
      id: `inferred-attempts-${job.id}`,
      at: job.updated_at,
      title: "Attempt count updated",
      detail: `Inferred attempts=${job.attempts}/${job.max_attempts}.`,
      source: "inferred",
    });
  }

  if (job.cancel_requested) {
    events.push({
      id: `inferred-cancel-${job.id}`,
      at: job.updated_at,
      title: "Cancel requested",
      detail: "Inferred from cancel_requested=true.",
      source: "inferred",
    });
  }

  if (job.orchestration_id) {
    events.push({
      id: `inferred-orchestration-${job.id}`,
      at: job.updated_at,
      title: "Orchestration linked",
      detail: `Inferred linked orchestration_id=${job.orchestration_id}.`,
      source: "inferred",
    });
  }

  if (job.error_message) {
    events.push({
      id: `inferred-error-${job.id}`,
      at: job.updated_at,
      title: "Error captured",
      detail: `Inferred from error_message: ${job.error_message}`,
      source: "inferred",
    });
  }

  return {
    mode: "inferred",
    events: events.sort((a, b) => a.at.localeCompare(b.at)),
  };
}

export function buildQueueTimelineReplay(job: WorkflowQueueJob): QueueTimelineReplay {
  const maybeWithEvents = job as QueueJobWithOptionalEvents;
  if (!maybeWithEvents.events || maybeWithEvents.events.length === 0) {
    return inferTimeline(job);
  }

  const observedEvents = maybeWithEvents.events.map((event, index) => {
    const at = normalizeTimestamp(event.at, job.updated_at);
    return {
      id: `observed-${job.id}-${index}`,
      at,
      title: event.event?.trim() || inferredStatusTitle(event.status ?? job.status),
      detail: event.detail?.trim() || `Observed status=${event.status ?? job.status}.`,
      source: "observed" as const,
    };
  });

  return {
    mode: "event_log",
    events: observedEvents.sort((a, b) => a.at.localeCompare(b.at)),
  };
}

