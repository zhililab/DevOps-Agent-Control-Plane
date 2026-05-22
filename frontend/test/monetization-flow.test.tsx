import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import MonetizationPage from "@/app/monetization/page";

const profile = {
  id: 1,
  subject: "demo-user",
  tier: "pro",
  status: "active",
  billing_provider: "manual",
  external_customer_id: "",
  external_subscription_id: "",
  current_period_start: "2026-05-01T00:00:00Z",
  current_period_end: "2026-05-31T23:59:59Z",
  cancel_at_period_end: false,
  entitlements: { workflow_runs: 300, queued_runs: 300 },
  created_at: "2026-05-22T00:00:00Z",
  updated_at: "2026-05-22T00:00:00Z",
};

const counters = [
  {
    id: 10,
    subscription_profile_id: 1,
    metric: "workflow_runs",
    period_start: "2026-05-01",
    period_end: "2026-05-31",
    used: 4,
    limit: 300,
    created_at: "2026-05-22T00:00:00Z",
    updated_at: "2026-05-22T00:00:00Z",
  },
  {
    id: 11,
    subscription_profile_id: 1,
    metric: "queued_runs",
    period_start: "2026-05-01",
    period_end: "2026-05-31",
    used: 1,
    limit: 300,
    created_at: "2026-05-22T00:00:00Z",
    updated_at: "2026-05-22T00:00:00Z",
  },
];

const commercialMetrics = {
  window_days: 7,
  generated_at: "2026-05-22T00:00:00Z",
  subject: "demo-user",
  subscription_summary: {
    active_subjects: 1,
    profile_count: 1,
    tier_distribution: { free: 0, pro: 1, power: 0 },
    status_distribution: { inactive: 0, active: 1, past_due: 0, canceled: 0 },
  },
  usage_summary: {
    workflow_runs_used: 4,
    workflow_runs_limit: 300,
    queued_runs_used: 1,
    queued_runs_limit: 300,
    usage_subjects: 1,
  },
  plan_usage: {
    workflow_runs_used: 4,
    workflow_runs_limit: 300,
    queued_runs_used: 1,
    queued_runs_limit: 300,
    period_start: "2026-05-01",
    period_end: "2026-05-31",
  },
  commercial_events: [{ action: "checkout completed", count: 1 }],
  policy_blocks: {
    approval_required: 1,
    upgrade_required: 2,
    quota_exceeded: 0,
    total: 3,
  },
  billable_work_units: {
    total: 21,
    audited_workflows: 4,
    average_per_run: 5.25,
  },
  top_templates: [
    {
      template_id: 7,
      template_name: "Release Gate And Remote Deploy",
      runs: 3,
      billable_work_units: 15,
      required_tier: "power",
      risk_level: "high",
      approval_required: true,
    },
  ],
  trend: [{ date: "2026-05-22", billable_work_units: 21, audited_workflows: 4, policy_blocks: 3 }],
  anomaly_hints: [],
};

function event(action: string, tier = "pro") {
  return {
    id: action === "cancel_requested" ? 22 : 21,
    subscription_profile_id: 1,
    usage_counter_id: null,
    event_kind: "subscription_changed",
    event: { action, provider: "manual", new_tier: tier },
    created_at: "2026-05-22T00:00:00Z",
  };
}

function abortError() {
  const error = new Error("aborted");
  error.name = "AbortError";
  return error;
}

describe("monetization flow", () => {
  beforeEach(() => {
    vi.mocked(globalThis.fetch).mockReset();
  });

  test("activates a manual plan and renders usage plus audit feed", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/monetization/profile")) {
        return new Response(JSON.stringify({ profile }), { status: 200 });
      }
      if (url.includes("/monetization/usage")) {
        return new Response(JSON.stringify({ counters }), { status: 200 });
      }
      if (url.includes("/monetization/events")) {
        return new Response(JSON.stringify({ events: [event("checkout_completed")] }), { status: 200 });
      }
      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetrics), { status: 200 });
      }
      if (url.endsWith("/monetization/checkout/manual")) {
        return new Response(JSON.stringify({ profile, counters, event: event("tier_changed", "power") }), {
          status: 200,
        });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MonetizationPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/PRO · active/).length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("heading", { name: "Plans & Usage" })).toBeInTheDocument();
    expect(screen.getByText("COMMERCIAL MVP")).toBeInTheDocument();
    expect(screen.getByText("Turn trusted DevOps runs into metered plans.")).toBeInTheDocument();
    expect(screen.getByText("Plan Usage")).toBeInTheDocument();
    expect(screen.getByText("Current billing period")).toBeInTheDocument();
    expect(screen.getByText("Workflow Runs")).toBeInTheDocument();
    expect(screen.getAllByText("4 / 300").length).toBeGreaterThan(0);
    expect(screen.getAllByText("checkout completed").length).toBeGreaterThan(0);
    expect(screen.getByText("Commercial Audit Feed")).toBeInTheDocument();
    expect(screen.queryByText("Commercial Metrics V2")).not.toBeInTheDocument();
    expect(screen.getByText("Commercial Signal")).toBeInTheDocument();
    expect(screen.getByText("7D activity & ROI")).toBeInTheDocument();
    expect(screen.getByText("Release Gate And Remote Deploy")).toBeInTheDocument();
    expect(screen.getAllByText("21").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Activate Power" }));

    await waitFor(() => {
      expect(screen.getByText("POWER subscription is active.")).toBeInTheDocument();
    });
    const checkoutCall = fetchMock.mock.calls.find(([input]) => input.toString().endsWith("/monetization/checkout/manual"));
    expect(checkoutCall?.[1]?.body).toBe(JSON.stringify({ subject: "demo-user", target_tier: "power" }));
  });

  test("keeps profile and usage visible when audit feed refresh times out", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/monetization/profile")) {
        return new Response(JSON.stringify({ profile }), { status: 200 });
      }
      if (url.includes("/monetization/usage")) {
        return new Response(JSON.stringify({ counters }), { status: 200 });
      }
      if (url.includes("/monetization/events")) {
        return Promise.reject(abortError());
      }
      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetrics), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MonetizationPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/PRO · active/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("4 / 300").length).toBeGreaterThan(0);
    expect(screen.getByText(/missing: commercial audit feed/)).toBeInTheDocument();
    expect(screen.queryByText("Request timed out. Please retry.")).not.toBeInTheDocument();
    expect(screen.queryByText("No subscription profile")).not.toBeInTheDocument();
  });

  test("uses lifecycle response when post-action refresh times out", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let checkoutCompleted = false;
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/monetization/checkout/manual")) {
        checkoutCompleted = true;
        return new Response(JSON.stringify({ profile, counters, event: event("tier_changed") }), { status: 200 });
      }
      if (checkoutCompleted && url.includes("/monetization/")) {
        return Promise.reject(abortError());
      }
      if (url.includes("/monetization/profile")) {
        return new Response(JSON.stringify({ profile: null }), { status: 200 });
      }
      if (url.includes("/monetization/usage")) {
        return new Response(JSON.stringify({ counters: [] }), { status: 200 });
      }
      if (url.includes("/monetization/events")) {
        return new Response(JSON.stringify({ events: [] }), { status: 200 });
      }
      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetrics), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MonetizationPage />);

    await waitFor(() => {
      expect(screen.getByText("No subscription profile")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Activate Pro" }));

    await waitFor(() => {
      expect(screen.getByText("PRO subscription is active.")).toBeInTheDocument();
    });
    expect(screen.getAllByText(/PRO · active/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("4 / 300").length).toBeGreaterThan(0);
    expect(screen.getByText("Commercial data could not refresh. Showing the latest subscription update when available.")).toBeInTheDocument();
    expect(screen.queryByText("Request timed out. Please retry.")).not.toBeInTheDocument();
  });

  test("cancel and reactivate subscription controls update visible state", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let cancelPending = false;
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      const currentProfile = { ...profile, cancel_at_period_end: cancelPending };
      if (url.includes("/monetization/profile")) {
        return new Response(JSON.stringify({ profile: currentProfile }), { status: 200 });
      }
      if (url.includes("/monetization/usage")) {
        return new Response(JSON.stringify({ counters }), { status: 200 });
      }
      if (url.includes("/monetization/events")) {
        return new Response(JSON.stringify({ events: [event(cancelPending ? "cancel_requested" : "reactivated")] }), {
          status: 200,
        });
      }
      if (url.includes("/monetization/commercial-metrics")) {
        return new Response(JSON.stringify(commercialMetrics), { status: 200 });
      }
      if (url.endsWith("/monetization/cancel")) {
        cancelPending = true;
        return new Response(JSON.stringify({ profile: { ...profile, cancel_at_period_end: true }, counters, event: event("cancel_requested") }), {
          status: 200,
        });
      }
      if (url.endsWith("/monetization/reactivate")) {
        cancelPending = false;
        return new Response(JSON.stringify({ profile, counters, event: event("reactivated") }), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MonetizationPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/PRO · active/).length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancel At Period End" }));
    await waitFor(() => {
      expect(screen.getByText("Cancellation is scheduled at period end.")).toBeInTheDocument();
    });
    expect(screen.getByText("Cancellation pending at period end.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reactivate" }));
    await waitFor(() => {
      expect(screen.getByText("Subscription reactivated.")).toBeInTheDocument();
    });
  });
});
