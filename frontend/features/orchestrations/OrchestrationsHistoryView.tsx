"use client";

import { useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type { WorkflowOrchestrationRecord } from "@/lib/types";

export function OrchestrationsHistoryView() {
  const [items, setItems] = useState<WorkflowOrchestrationRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "success" | "partial_success" | "failed" | "canceled">("all");
  const [tierFilter, setTierFilter] = useState<"all" | "free" | "pro" | "power">("all");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiClient.listWorkflowOrchestrations({
          status: statusFilter === "all" ? undefined : statusFilter,
          subscription_tier: tierFilter === "all" ? undefined : tierFilter,
          limit: 50,
        });
        setItems(response.items);
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
        <section key={item.id} className="history-plan">
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
    </PageCard>
  );
}
