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
      if (url.endsWith("/monetization/checkout/manual")) {
        return new Response(JSON.stringify({ profile, counters, event: event("tier_changed", "power") }), {
          status: 200,
        });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MonetizationPage />);

    await waitFor(() => {
      expect(screen.getByText(/PRO · active/)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "Plans & Usage" })).toBeInTheDocument();
    expect(screen.getByText("Govern")).toBeInTheDocument();
    expect(screen.getByText("Workflow Runs")).toBeInTheDocument();
    expect(screen.getByText("4 / 300")).toBeInTheDocument();
    expect(screen.getByText("checkout completed")).toBeInTheDocument();
    expect(screen.getByText("Commercial Audit Feed")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Activate Power" }));

    await waitFor(() => {
      expect(screen.getByText("POWER subscription is active.")).toBeInTheDocument();
    });
    const checkoutCall = fetchMock.mock.calls.find(([input]) => input.toString().endsWith("/monetization/checkout/manual"));
    expect(checkoutCall?.[1]?.body).toBe(JSON.stringify({ subject: "demo-user", target_tier: "power" }));
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
      expect(screen.getByText(/PRO · active/)).toBeInTheDocument();
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
