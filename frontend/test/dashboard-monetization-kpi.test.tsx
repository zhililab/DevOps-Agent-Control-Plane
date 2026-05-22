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

    expect(within(runCard!).getByText("11")).toBeInTheDocument();
    expect(within(runCard!).getByText("+11 vs previous 7D")).toBeInTheDocument();
    expect(within(waoCard!).getByText("9")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("37.5%")).toBeInTheDocument();
    expect(within(partialSuccessCard!).getByText("+37.5pp vs previous 7D")).toBeInTheDocument();
    expect(within(avgDurationCard!).getByText("1.5s")).toBeInTheDocument();
    expect(within(workUnitsCard!).getByText("27")).toBeInTheDocument();
    expect(within(auditedCard!).getByText("10")).toBeInTheDocument();
    expect(within(policyBlocksCard!).getByText("3")).toBeInTheDocument();

    const revenueCard = screen.getByText("Revenue").closest("article");
    const paidRunsCard = screen.getByText("Paid Runs").closest("article");
    const conversionCard = screen.getByText("Conversion Rate").closest("article");
    const failedPaymentCard = screen.getByText("Failed Payment Rate").closest("article");
    expect(within(revenueCard!).getByText("$231.50")).toBeInTheDocument();
    expect(within(paidRunsCard!).getByText("14")).toBeInTheDocument();
    expect(within(conversionCard!).getByText("28.0%")).toBeInTheDocument();
    expect(within(failedPaymentCard!).getByText("4.0%")).toBeInTheDocument();
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
