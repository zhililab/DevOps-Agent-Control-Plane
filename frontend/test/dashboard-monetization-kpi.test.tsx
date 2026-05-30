import { render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";

describe("dashboard monetization kpi", () => {
  test("renders orchestration monetization kpis from metrics contract", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/plans/history") || url.includes("/reflections/history") || url.includes("/analysis/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/orchestrations/metrics")) {
        return new Response(
          JSON.stringify({
            period_days: 7,
            total_runs: 11,
            weekly_active_orchestrations: 9,
            partial_success_rate: 0.375,
            average_duration_ms: 1500,
            billable_work_units: 27,
            successful_audited_workflows: 10,
            approval_required_blocks: 2,
            template_policy_upgrade_blocks: 1,
            approved_runs: 8,
            checkpointed_runs: 10,
            failed_jobs_needing_owner: 1,
          }),
          { status: 200 }
        );
      }

      if (url.includes("/orchestrations/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/observability/monetization")) {
        return new Response(
          JSON.stringify({
            observability: {
              period_days: 7,
              kpis: {
                total_revenue_usd: 231.5,
                paid_runs: 14,
                conversion_rate: 0.28,
                failed_payment_rate: 0.04,
              },
              trend: [],
              health: {
                status: "healthy",
                summary: "No monetization incidents in the selected window.",
                incidents: [],
              },
            },
          }),
          { status: 200 }
        );
      }

      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(
          JSON.stringify({
            window_days: 7,
            generated_at: "2026-05-22T00:00:00Z",
            subject: null,
            subscription_summary: {
              active_subjects: 2,
              profile_count: 2,
              tier_distribution: { free: 0, pro: 1, power: 1 },
              status_distribution: { inactive: 0, active: 2, past_due: 0, canceled: 0 },
            },
            usage_summary: {
              workflow_runs_used: 9,
              workflow_runs_limit: 2300,
              queued_runs_used: 2,
              queued_runs_limit: 2300,
              usage_subjects: 2,
            },
            plan_usage: {
              workflow_runs_used: 9,
              workflow_runs_limit: 2300,
              queued_runs_used: 2,
              queued_runs_limit: 2300,
              period_start: "2026-05-01",
              period_end: "2026-05-31",
            },
            commercial_events: [{ action: "checkout completed", count: 2 }],
            policy_blocks: {
              approval_required: 1,
              upgrade_required: 2,
              quota_exceeded: 0,
              total: 3,
            },
            billable_work_units: {
              total: 31,
              audited_workflows: 8,
              average_per_run: 3.88,
            },
            roi_summary: {
              runs_with_roi: 8,
              estimated_customer_value_usd: 18400,
              review_time_saved_minutes: 220,
              audit_time_saved_minutes: 140,
              blocked_risk_count: 3,
              blocked_risk_value_usd: 15000,
              billable_work_units: 31,
              work_units_by_template: [],
            },
            top_templates: [],
            trend: [{ date: "2026-05-22", billable_work_units: 31, audited_workflows: 8, policy_blocks: 3 }],
            anomaly_hints: [{ code: "policy_blocks_high", severity: "warning", message: "3 policy block(s) appeared in this window." }],
          }),
          { status: 200 }
        );
      }

      if (url.includes("/monetization/pilot-report")) {
        return new Response(
          JSON.stringify({
            window_days: 7,
            generated_at: "2026-05-22T00:00:00Z",
            subject: null,
            team_subject: null,
            status: "ready",
            runs_completed: 5,
            evidence_exportable_runs: 5,
            ledger_valid_runs: 5,
            checkpointed_runs: 5,
            approval_required_runs: 4,
            blocked_or_needs_review_runs: 3,
            estimated_value_usd: 18400,
            review_time_saved_minutes: 220,
            audit_time_saved_minutes: 140,
            metadata_completeness: 0.9,
            missing_metadata_runs: 0,
            scenario_statuses: [],
            power_upgrade_evidence: {
              power_required_runs: 5,
              approval_required_runs: 4,
              blocked_or_needs_review_runs: 3,
              evidence_exportable_runs: 5,
              ledger_valid_runs: 5,
              estimated_value_usd: 18400,
              review_audit_time_saved_minutes: 360,
              recommendation: "Power is the recommended pilot plan.",
            },
            success_criteria: [],
            recommendations: [],
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({ detail: `Unhandled mock url: ${url}` }), { status: 500 });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Orchestration Runs")).toBeInTheDocument();
    });

    const runCard = screen.getByText("Orchestration Runs").closest("article");
    const waoCard = screen.getByText("Weekly Active Orchestrations").closest("article");
    const partialSuccessCard = screen.getByText("Partial Success Rate").closest("article");
    const avgDurationCard = screen.getByText("Avg Orchestration Duration").closest("article");
    const workUnitsCard = screen.getByText("Billable Work Units").closest("article");
    const auditedCard = screen.getByText("Audited Workflows").closest("article");
    const policyBlocksCard = screen.getByText("Policy Blocks").closest("article");
    const approvedRunsCard = screen.getByText("Approved Runs").closest("article");
    const checkpointedRunsCard = screen.getByText("Checkpointed Runs").closest("article");
    const jobsNeedingOwnerCard = screen.getByText("Jobs Needing Owner").closest("article");

    expect(within(runCard!).getByText("11")).toBeInTheDocument();
    expect(within(runCard!).getByText("+11 vs previous 7D")).toBeInTheDocument();
    expect(within(waoCard!).getByText("9")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("37.5%")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("+37.5pp vs previous 7D")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("1.5s")).toBeInTheDocument();
    expect(within(workUnitsCard!).getByText("27")).toBeInTheDocument();
    expect(within(auditedCard!).getByText("10")).toBeInTheDocument();
    expect(within(policyBlocksCard!).getByText("3")).toBeInTheDocument();
    expect(within(approvedRunsCard!).getByText("8")).toBeInTheDocument();
    expect(within(checkpointedRunsCard!).getByText("10")).toBeInTheDocument();
    expect(within(jobsNeedingOwnerCard!).getByText("1")).toBeInTheDocument();

    const revenueCard = screen.getByText("Revenue").closest("article");
    const paidRunsCard = screen.getByText("Paid Runs").closest("article");
    const conversionCard = screen.getByText("Conversion Rate").closest("article");
    const failedPaymentCard = screen.getByText("Failed Payment Rate").closest("article");
    expect(within(revenueCard!).getByText("$231.50")).toBeInTheDocument();
    expect(within(paidRunsCard!).getByText("14")).toBeInTheDocument();
    expect(within(conversionCard!).getByText("28.0%")).toBeInTheDocument();
    expect(within(failedPaymentCard!).getByText("4.0%")).toBeInTheDocument();
    const commercialWorkUnitsCard = screen.getAllByText("Commercial Work Units")[0].closest("article");
    const commercialPolicyBlocksCard = screen.getByText("Commercial Policy Blocks").closest("article");
    const estimatedValueCard = screen.getByText("Estimated Value").closest("article");
    const reviewTimeSavedCard = screen.getByText("Review Time Saved").closest("article");
    const blockedRiskValueCard = screen.getByText("Blocked Risk Value").closest("article");
    const pilotReadyCard = screen.getByText("Pilot Ready").closest("article");
    expect(within(commercialWorkUnitsCard!).getByText("31")).toBeInTheDocument();
    expect(within(commercialPolicyBlocksCard!).getByText("3")).toBeInTheDocument();
    expect(within(estimatedValueCard!).getByText("$18,400.00")).toBeInTheDocument();
    expect(within(reviewTimeSavedCard!).getByText("360m")).toBeInTheDocument();
    expect(within(blockedRiskValueCard!).getByText("$15,000.00")).toBeInTheDocument();
    expect(within(pilotReadyCard!).getByText("READY")).toBeInTheDocument();
    expect(within(pilotReadyCard!).getByText("5 runs · 90% metadata")).toBeInTheDocument();
    expect(screen.getByText(/3 policy block\(s\) appeared/)).toBeInTheDocument();
  });

  test("falls back to zero-value monetization kpis when metrics payload shape is invalid", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/plans/history") || url.includes("/reflections/history") || url.includes("/analysis/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/orchestrations/metrics")) {
        return new Response(
          JSON.stringify({
            period_days: 7,
            total_runs: 11,
          }),
          { status: 200 }
        );
      }

      if (url.includes("/orchestrations/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.includes("/observability/monetization")) {
        return new Response(
          JSON.stringify({
            observability: {
              period_days: 7,
              kpis: {
                total_revenue_usd: 120,
                paid_runs: 5,
                conversion_rate: 0.11,
                failed_payment_rate: 0.02,
              },
              trend: [],
              health: {
                status: "healthy",
                summary: "No incidents.",
                incidents: [],
              },
            },
          }),
          { status: 200 }
        );
      }

      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify({ invalid: true }), { status: 200 });
      }

      return new Response(JSON.stringify({ detail: `Unhandled mock url: ${url}` }), { status: 500 });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Some dashboard data is unavailable:/)).toBeInTheDocument();
    });

    const runCard = screen.getByText("Orchestration Runs").closest("article");
    const waoCard = screen.getByText("Weekly Active Orchestrations").closest("article");
    const partialSuccessCard = screen.getByText("Partial Success Rate").closest("article");
    const avgDurationCard = screen.getByText("Avg Orchestration Duration").closest("article");

    expect(within(runCard!).getByText("0")).toBeInTheDocument();
    expect(within(runCard!).getByText("0 vs previous 7D")).toBeInTheDocument();
    expect(within(waoCard!).getByText("0")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("0.0%")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("0.0pp vs previous 7D")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("0ms")).toBeInTheDocument();
  });
});
