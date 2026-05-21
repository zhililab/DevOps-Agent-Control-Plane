"use client";

import { useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import { formatBusinessTimestamp } from "@/lib/time";
import type { DailyPlanRecord } from "@/lib/types";

export function HistoryView() {
  const [plans, setPlans] = useState<DailyPlanRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiClient.listDailyPlans();
        setPlans(response.items);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load plan history");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, []);

  return (
    <PageCard title="History" description="Saved daily plans.">
      {error ? <p className="status status-error">{error}</p> : null}

      {isLoading ? <p className="muted">Loading plan history...</p> : null}
      {!isLoading && plans.length === 0 ? <p className="muted">No plans saved yet.</p> : null}

      {plans.map((plan) => (
        <section key={plan.id} className="history-plan">
          <h3>{formatBusinessTimestamp(plan.created_at, plan.business_timezone)}</h3>
          <p className="muted">Business date: {plan.plan_date}</p>
          <p>{plan.plan.status_summary}</p>

          <div className="result-grid">
            <div className="result-block">
              <h4>Top Priorities</h4>
              <ul>
                {plan.plan.top_priorities.map((item) => (
                  <li key={`history-priority-${plan.id}-${item}`}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="result-block">
              <h4>Recommended Order</h4>
              <ol>
                {plan.plan.recommended_order.map((item) => (
                  <li key={`history-order-${plan.id}-${item}`}>{item}</li>
                ))}
              </ol>
            </div>

            <div className="result-block">
              <h4>Risks And Reminders</h4>
              <ul>
                {plan.plan.risks_and_reminders.map((item) => (
                  <li key={`history-risk-${plan.id}-${item}`}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="result-block">
              <h4>Next Actions</h4>
              <ul>
                {plan.plan.next_actions.map((item) => (
                  <li key={`history-next-${plan.id}-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ))}
    </PageCard>
  );
}
