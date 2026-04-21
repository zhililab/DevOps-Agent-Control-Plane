import { render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";

describe("dashboard flow", () => {
  test("shows partial data and friendly error when one endpoint fails", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementationOnce(async () =>
      new Response(
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
      )
    );
    fetchMock.mockImplementationOnce(async () => new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }));
    fetchMock.mockImplementationOnce(async () =>
      new Response(
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
      )
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Some dashboard data is unavailable: reflections.")).toBeInTheDocument();
    });

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
  });
});
