import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import HistoryPage from "@/app/history/page";
import TodayPage from "@/app/today/page";

describe("daily planning workflow", () => {
  test("submits context and renders structured daily plan", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/plans/daily")) {
        return new Response(
          JSON.stringify({
            id: 11,
            plan_date: "2026-04-16",
            context: {
              tasks: ["Fix CI flake", "Prepare release notes"],
              meetings: ["10:30 Platform sync"],
              blockers: ["Need infra approval"],
              priorities: ["Fix CI flake"],
            },
            plan: {
              top_priorities: ["Fix CI flake"],
              recommended_order: ["Fix CI flake", "Prepare release notes"],
              risks_and_reminders: ["Blocker risk: Need infra approval"],
              next_actions: ["Start with: Fix CI flake", "Resolve blocker quickly"],
              status_summary: "Planned 2 task(s), 1 meeting(s), and 1 blocker(s). Primary focus: Fix CI flake",
            },
            created_at: "2026-04-16T08:00:00Z",
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<TodayPage />);

    fireEvent.change(screen.getByLabelText("Tasks (one per line)"), {
      target: { value: "Fix CI flake\nPrepare release notes" },
    });
    fireEvent.change(screen.getByLabelText("Meetings (one per line)"), {
      target: { value: "10:30 Platform sync" },
    });
    fireEvent.change(screen.getByLabelText("Blockers (one per line)"), {
      target: { value: "Need infra approval" },
    });
    fireEvent.change(screen.getByLabelText("Priorities (one per line)"), {
      target: { value: "Fix CI flake" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate Daily Plan" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Generated Plan" })).toBeInTheDocument();
    });
    expect(screen.getByText("Prepare release notes")).toBeInTheDocument();
    expect(screen.getByText("Blocker risk: Need infra approval")).toBeInTheDocument();
    expect(screen.getByText("Start with: Fix CI flake")).toBeInTheDocument();
  });

  test("renders structured history for saved plans", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/plans/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 22,
                plan_date: "2026-05-22",
                context: {
                  tasks: ["Ship release"],
                  meetings: ["Daily sync"],
                  blockers: ["Pending signoff"],
                  priorities: ["Ship release"],
                },
                plan: {
                  top_priorities: ["Ship release"],
                  recommended_order: ["Ship release", "Prepare for meeting: Daily sync"],
                  risks_and_reminders: ["Blocker risk: Pending signoff"],
                  next_actions: ["Start with: Ship release"],
                  status_summary: "Planned 1 task(s), 1 meeting(s), and 1 blocker(s). Primary focus: Ship release",
                },
                created_at: "2026-05-21T16:45:36Z",
                record_source: "user",
                business_timezone: "Asia/Shanghai",
              },
            ],
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Top Priorities" })).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "2026-05-22 · 00:45:36 GMT+8" })).toBeInTheDocument();
    expect(screen.getByText("Business date: 2026-05-22")).toBeInTheDocument();
    expect(screen.getByText("Prepare for meeting: Daily sync")).toBeInTheDocument();
    expect(screen.getByText("Blocker risk: Pending signoff")).toBeInTheDocument();
    expect(screen.getByText("Start with: Ship release")).toBeInTheDocument();
  });

  test("shows sanitized error when plan history endpoint fails", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/plans/history")) {
        return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("The requested data was not found.")).toBeInTheDocument();
    });
    expect(screen.queryByText('{"detail":"Not Found"}')).not.toBeInTheDocument();
  });
});
