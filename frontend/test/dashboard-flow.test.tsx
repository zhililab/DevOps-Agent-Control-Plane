import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";

function toIsoDay(daysAgo: number, hour = 8): string {
  const current = new Date();
  current.setDate(current.getDate() - daysAgo);
  const day = current.toISOString().slice(0, 10);
  return `${day}T${String(hour).padStart(2, "0")}:00:00Z`;
}

const commercialMetricsPayload = {
  window_days: 7,
  generated_at: "2026-05-22T00:00:00Z",
  subject: null,
  subscription_summary: {
    active_subjects: 0,
    profile_count: 0,
    tier_distribution: { free: 0, pro: 0, power: 0 },
    status_distribution: { inactive: 0, active: 0, past_due: 0, canceled: 0 },
  },
  usage_summary: {
    workflow_runs_used: 0,
    workflow_runs_limit: 0,
    queued_runs_used: 0,
    queued_runs_limit: 0,
    usage_subjects: 0,
  },
  plan_usage: {
    workflow_runs_used: 0,
    workflow_runs_limit: 0,
    queued_runs_used: 0,
    queued_runs_limit: 0,
    period_start: null,
    period_end: null,
  },
  commercial_events: [],
  policy_blocks: { approval_required: 0, upgrade_required: 0, quota_exceeded: 0, total: 0 },
  billable_work_units: { total: 0, audited_workflows: 0, average_per_run: 0 },
  top_templates: [],
  trend: [],
  anomaly_hints: [],
};

describe("dashboard flow", () => {
  test("shows partial data and friendly error when one endpoint fails", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/plans/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 1,
                plan_date: "2026-04-20",
                context: { tasks: ["A"], meetings: [], blockers: [], priorities: [] },
                plan: {
                  top_priorities: ["A"],
                  recommended_order: [],
                  risks_and_reminders: [],
                  next_actions: [],
                  status_summary: "ok",
                },
                created_at: "2026-04-20T00:00:00Z",
              },
            ],
          }),
          { status: 200 }
        );
      }

      if (url.includes("/reflections/history")) {
        return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
      }

      if (url.includes("/analysis/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 3,
                analysis_date: "2026-04-20",
                input: {
                  logs: "",
                  errors: [],
                  code_snippets: [],
                  issue_description: "deploy timeout",
                },
                output: {
                  problem_statement: "timeout",
                  likely_causes: [],
                  validation_steps: [],
                  fix_options: [],
                  risks: [],
                  follow_up_tasks: [],
                },
                created_at: "2026-04-20T00:00:00Z",
              },
            ],
          }),
          { status: 200 }
        );
      }

      if (url.includes("/orchestrations/metrics?days=30")) {
        return new Response(
          JSON.stringify({
            period_days: 30,
            total_runs: 22,
            weekly_active_orchestrations: 15,
            partial_success_rate: 0.1,
            average_duration_ms: 940,
            billable_work_units: 32,
            successful_audited_workflows: 20,
            approval_required_blocks: 1,
            template_policy_upgrade_blocks: 2,
            approved_runs: 18,
            checkpointed_runs: 20,
            failed_jobs_needing_owner: 1,
          }),
          { status: 200 }
        );
      }

      if (url.includes("/orchestrations/metrics?days=7")) {
        return new Response(
          JSON.stringify({
            period_days: 7,
            total_runs: 4,
            weekly_active_orchestrations: 3,
            partial_success_rate: 0.75,
            average_duration_ms: 1850,
            billable_work_units: 9,
            successful_audited_workflows: 4,
            approval_required_blocks: 1,
            template_policy_upgrade_blocks: 0,
            approved_runs: 3,
            checkpointed_runs: 4,
            failed_jobs_needing_owner: 1,
          }),
          { status: 200 }
        );
      }

      if (url.includes("/orchestrations/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 11,
                status: "partial_success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(6),
                updated_at: toIsoDay(6),
              },
              {
                id: 12,
                status: "partial_success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(5),
                updated_at: toIsoDay(5),
              },
              {
                id: 13,
                status: "failed",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(3),
                updated_at: toIsoDay(3),
              },
              {
                id: 14,
                status: "partial_success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(1),
                updated_at: toIsoDay(1),
              },
              {
                id: 15,
                status: "failed",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(13),
                updated_at: toIsoDay(13),
              },
              {
                id: 16,
                status: "failed",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(12),
                updated_at: toIsoDay(12),
              },
              {
                id: 17,
                status: "success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(11),
                updated_at: toIsoDay(11),
              },
              {
                id: 18,
                status: "failed",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(10),
                updated_at: toIsoDay(10),
              },
              {
                id: 19,
                status: "partial_success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(9),
                updated_at: toIsoDay(9),
              },
              {
                id: 20,
                status: "success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(8),
                updated_at: toIsoDay(8),
              },
              {
                id: 21,
                status: "failed",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(7),
                updated_at: toIsoDay(7),
              },
              {
                id: 22,
                status: "success",
                duration_ms: 1200,
                entry_source: "manual",
                subscription_tier: "pro",
                summary: {
                  conclusion: "ok",
                  risks: [],
                  next_actions: [],
                },
                steps: [],
                created_at: toIsoDay(7, 10),
                updated_at: toIsoDay(7, 10),
              },
            ],
          }),
          { status: 200 }
        );
      }

      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetricsPayload), { status: 200 });
      }

      return new Response(JSON.stringify({ detail: `Unhandled mock url: ${url}` }), { status: 500 });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Some dashboard data is unavailable:/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Some dashboard data is unavailable: reflections\./)).toBeInTheDocument();

    expect(screen.queryByText('{"detail":"Not Found"}')).not.toBeInTheDocument();

    const plansCard = screen.getByText("Saved Daily Plans").closest("article");
    const reflectionsCard = screen.getByText("Saved Reflections").closest("article");
    const analysisCard = screen.getByText("Technical Analyses").closest("article");

    expect(plansCard).not.toBeNull();
    expect(reflectionsCard).not.toBeNull();
    expect(analysisCard).not.toBeNull();

    expect(within(plansCard!).getByText("1")).toBeInTheDocument();
    expect(within(reflectionsCard!).getByText("0")).toBeInTheDocument();
    expect(within(analysisCard!).getByText("1")).toBeInTheDocument();

    const waoCard = screen.getByText("Weekly Active Orchestrations").closest("article");
    const runCard = screen.getByText("Orchestration Runs").closest("article");
    const partialSuccessCard = screen.getByText("Partial Success Rate").closest("article");
    const avgDurationCard = screen.getByText("Avg Orchestration Duration").closest("article");

    expect(runCard).not.toBeNull();
    expect(waoCard).not.toBeNull();
    expect(partialSuccessCard).not.toBeNull();
    expect(avgDurationCard).not.toBeNull();

    expect(within(runCard!).getByText("4")).toBeInTheDocument();
    expect(within(runCard!).getByText("-4 vs previous 7D")).toBeInTheDocument();
    expect(within(waoCard!).getByText("3")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("75.0%")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("+62.5pp vs previous 7D")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("1.9s")).toBeInTheDocument();
    expect(
      screen.getByText(/Anomaly hint: Sharp run drop: 4 runs vs 8 in the previous 7-day window\./)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anomaly hint: Partial-success\/fail ratio spiked from 0.40 to 2.00\./)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Orchestration Activity trend chart" })).toBeInTheDocument();

    const switchTo30Days = screen.getByRole("button", { name: "30D Window" });
    fireEvent.click(switchTo30Days);

    await waitFor(() => {
      expect(within(runCard!).getByText("22")).toBeInTheDocument();
      expect(within(waoCard!).getByText("15")).toBeInTheDocument();
    });
    expect(within(partialSuccessCard!).getByText("10.0%")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("940ms")).toBeInTheDocument();

    expect(screen.getByText("Workflow orchestrations in last 30 days")).toBeInTheDocument();
  });

  test("falls back to safe defaults when orchestration metrics endpoint fails", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/plans/history") || url.includes("/reflections/history") || url.includes("/analysis/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/orchestrations/metrics")) {
        return new Response(JSON.stringify({ detail: "boom" }), { status: 500 });
      }

      if (url.includes("/orchestrations/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetricsPayload), { status: 200 });
      }

      return new Response(JSON.stringify({ detail: `Unhandled mock url: ${url}` }), { status: 500 });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Some dashboard data is unavailable: orchestration metrics\./)).toBeInTheDocument();
    });

    const waoCard = screen.getByText("Weekly Active Orchestrations").closest("article");
    const runCard = screen.getByText("Orchestration Runs").closest("article");
    const partialSuccessCard = screen.getByText("Partial Success Rate").closest("article");
    const avgDurationCard = screen.getByText("Avg Orchestration Duration").closest("article");

    expect(within(runCard!).getByText("0")).toBeInTheDocument();
    expect(within(runCard!).getByText("0 vs previous 7D")).toBeInTheDocument();
    expect(within(waoCard!).getByText("0")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("0.0%")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("0.0pp vs previous 7D")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("0ms")).toBeInTheDocument();
    expect(screen.getByText("No orchestration anomalies detected for the selected window.")).toBeInTheDocument();
  });
});
