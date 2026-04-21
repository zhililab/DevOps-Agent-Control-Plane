import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import ReflectionPage from "@/app/reflection/page";

describe("reflection workflow", () => {
  test("submits reflection input and renders generated summary", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();

      if (url.endsWith("/reflections/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.endsWith("/reflections/daily")) {
        return new Response(
          JSON.stringify({
            id: 8,
            entry_date: "2026-04-16",
            input: {
              completed: ["Closed CI incident"],
              unfinished: ["Finalize release checklist"],
              blockers: ["Waiting for security approval"],
              mood_or_notes: "Focused but blocked by approvals",
            },
            summary: {
              day_summary:
                "Completed 1 item(s), led by 'Closed CI incident'. 1 item(s) remain unfinished. Blockers to watch: Waiting for security approval.",
              unfinished_items: ["Finalize release checklist"],
              pattern_hints: ["Blockers repeated today; escalate early before deep work starts."],
              tomorrow_suggestions: ["Start with unfinished item: Finalize release checklist"],
            },
            created_at: "2026-04-16T08:00:00Z",
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<ReflectionPage />);

    fireEvent.change(screen.getByLabelText("Completed (one per line)"), {
      target: { value: "Closed CI incident" },
    });
    fireEvent.change(screen.getByLabelText("Unfinished (one per line)"), {
      target: { value: "Finalize release checklist" },
    });
    fireEvent.change(screen.getByLabelText("Blockers (one per line)"), {
      target: { value: "Waiting for security approval" },
    });
    fireEvent.change(screen.getByLabelText("Mood or notes"), {
      target: { value: "Focused but blocked by approvals" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate Daily Summary" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Generated Daily Summary" })).toBeInTheDocument();
    });
    expect(screen.getByText("Reflection summary generated and saved.")).toBeInTheDocument();
    expect(
      screen.getByText("Blockers repeated today; escalate early before deep work starts.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Start with unfinished item: Finalize release checklist")
    ).toBeInTheDocument();
  });

  test("loads and shows reflection history", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();

      if (url.endsWith("/reflections/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 9,
                entry_date: "2026-04-15",
                input: {
                  completed: ["Ship release"],
                  unfinished: ["Write handover note"],
                  blockers: [],
                  mood_or_notes: "good",
                },
                summary: {
                  day_summary: "Completed 1 item(s), led by 'Ship release'. 1 item(s) remain unfinished.",
                  unfinished_items: ["Write handover note"],
                  pattern_hints: ["Execution moved, but closure lagged; protect a finish block tomorrow."],
                  tomorrow_suggestions: ["Start with unfinished item: Write handover note"],
                },
                created_at: "2026-04-15T08:00:00Z",
              },
            ],
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<ReflectionPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Reflection History" })).toBeInTheDocument();
    });
    expect(screen.getByText("2026-04-15")).toBeInTheDocument();
    expect(screen.getByText("Tomorrow: Start with unfinished item: Write handover note")).toBeInTheDocument();
  });
});
