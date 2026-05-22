import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import KnowledgePage from "@/app/knowledge/page";
import ReflectionPage from "@/app/reflection/page";
import TodayPage from "@/app/today/page";

describe("visual baseline", () => {
  test("dashboard baseline snapshot", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Knowledge Graph")).toBeInTheDocument();
    });

    const graphCard = screen.getByLabelText("Knowledge graph preview");
    expect(graphCard).toMatchSnapshot();
  });

  test("knowledge baseline snapshot", async () => {
    render(<KnowledgePage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Knowledge" })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText("No entries found.")).toBeInTheDocument();
    });

    const root = screen.getByRole("heading", { name: "Knowledge" }).closest("section");
    expect(root).not.toBeNull();
    expect(root).toMatchSnapshot();
  });

  test("today result-state baseline snapshot", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementationOnce(async () =>
      new Response(
        JSON.stringify({
          id: 9001,
          plan_date: "2026-04-21",
          context: {
            tasks: ["Finalize release notes"],
            meetings: ["10:30 Release sync"],
            blockers: ["Waiting for QA signoff"],
            priorities: ["Finalize release notes"],
          },
          plan: {
            top_priorities: ["Finalize release notes", "Run smoke tests"],
            recommended_order: ["Run smoke tests", "Publish release notes"],
            risks_and_reminders: ["QA signoff pending"],
            next_actions: ["Confirm QA owner", "Start smoke test checklist"],
            status_summary: "Release plan prepared with clear first actions.",
          },
          created_at: "2026-04-21T09:00:00Z",
        }),
        { status: 200 }
      )
    );

    render(<TodayPage />);
    fireEvent.click(screen.getByRole("button", { name: "Generate Daily Plan" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Generated Plan" })).toBeInTheDocument();
    });

    const generated = screen.getByRole("heading", { name: "Generated Plan" }).closest("div");
    expect(generated).not.toBeNull();
    expect(generated).toMatchSnapshot();
  });

  test("reflection result-state baseline snapshot", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementationOnce(async () => new Response(JSON.stringify({ items: [] }), { status: 200 }));
    fetchMock.mockImplementationOnce(async () =>
      new Response(
        JSON.stringify({
          id: 9101,
          entry_date: "2026-04-21",
          input: {
            completed: ["Closed CI incident"],
            unfinished: ["Finalize release checklist"],
            blockers: ["Waiting for security approval"],
            mood_or_notes: "Focused but dependency blocked.",
          },
          summary: {
            day_summary: "Core incident closed, but release closure is partially blocked by external approval.",
            unfinished_items: ["Finalize release checklist"],
            pattern_hints: ["External dependency delays handoff completion."],
            tomorrow_suggestions: ["Schedule security sync first thing tomorrow."],
          },
          created_at: "2026-04-21T10:00:00Z",
        }),
        { status: 200 }
      )
    );

    render(<ReflectionPage />);
    fireEvent.click(screen.getByRole("button", { name: "Generate Daily Summary" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Generated Daily Summary" })).toBeInTheDocument();
    });

    const generated = screen.getByRole("heading", { name: "Generated Daily Summary" }).closest("section");
    expect(generated).not.toBeNull();
    expect(generated).toMatchSnapshot();
  });
});
