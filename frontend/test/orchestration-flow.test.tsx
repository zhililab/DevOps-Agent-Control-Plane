import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import OrchestratePage from "@/app/orchestrate/page";
import OrchestrationsPage from "@/app/orchestrations/page";

describe("orchestration workflow", () => {
  test("runs orchestration and renders step replay", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith("/orchestrations/run")) {
        return new Response(
          JSON.stringify({
            id: 101,
            status: "success",
            duration_ms: 120,
            entry_source: "web_ui",
            subscription_tier: "pro",
            summary: {
              conclusion: "Reviewer summarized momentum with one carry-over action.",
              risks: ["Validation gaps can delay fixes."],
              next_actions: ["Run analyzer validation before merge."],
            },
            steps: [
              {
                id: 1,
                step_name: "Plan The Day",
                agent_type: "planner",
                status: "success",
                input_summary: "{}",
                output_summary: "Planner prioritized pipeline stabilization.",
                audit: {
                  conclusion: "Planner prioritized pipeline stabilization.",
                  evidence: "Input contained one blocker.",
                  risk: "Schedule drift if blocker persists.",
                  next_action: "Start with pipeline stabilization.",
                },
                fallback_action: "",
                started_at: "2026-04-23T00:00:00Z",
                finished_at: "2026-04-23T00:00:01Z",
                duration_ms: 100,
              },
            ],
            created_at: "2026-04-23T00:00:00Z",
            updated_at: "2026-04-23T00:00:01Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText("Run Replay")).toBeInTheDocument();
    });
    expect(screen.getByText(/Run #101/i)).toBeInTheDocument();
    expect(screen.getByText("Planner prioritized pipeline stabilization.")).toBeInTheDocument();
  });

  test("renders orchestration history with filters", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/orchestrations/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 202,
                status: "partial_success",
                duration_ms: 230,
                entry_source: "web_ui",
                subscription_tier: "pro",
                summary: {
                  conclusion: "Analyzer requested more technical evidence.",
                  risks: ["Missing logs may hide root cause."],
                  next_actions: ["Collect failing log snippet."],
                },
                steps: [
                  {
                    id: 11,
                    step_name: "Analyze Technical Signals",
                    agent_type: "analyzer",
                    status: "failed",
                    input_summary: "{}",
                    output_summary: "Analyzer could not validate issue.",
                    audit: {
                      conclusion: "Analyzer could not validate issue.",
                      evidence: "No technical input provided.",
                      risk: "Fixes without evidence can regress production.",
                      next_action: "Collect one concrete error signal.",
                    },
                    fallback_action: "Gather one concrete error signal and rerun analyzer.",
                    started_at: "2026-04-23T00:00:00Z",
                    finished_at: "2026-04-23T00:00:01Z",
                    duration_ms: 120,
                  },
                ],
                created_at: "2026-04-23T00:00:00Z",
                updated_at: "2026-04-23T00:00:01Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    render(<OrchestrationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Run #202 · partial_success · pro")).toBeInTheDocument();
    });
    expect(screen.getByText("Analyzer requested more technical evidence.")).toBeInTheDocument();
    expect(screen.getByText(/Fallback: Gather one concrete error signal/i)).toBeInTheDocument();
  });

  test("enqueues orchestration and displays queue status", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith("/orchestrations/queue/run")) {
        return new Response(
          JSON.stringify({
            job_id: 301,
            status: "queued",
            attempts: 0,
            max_attempts: 3,
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/301")) {
        return new Response(
          JSON.stringify({
            id: 301,
            status: "running",
            attempts: 1,
            max_attempts: 3,
            cancel_requested: false,
            orchestration_id: null,
            error_message: "",
            created_at: "2026-04-23T00:00:00Z",
            updated_at: "2026-04-23T00:00:01Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);

    fireEvent.change(screen.getByLabelText("Run Mode"), { target: { value: "async" } });
    fireEvent.click(screen.getByRole("button", { name: "Enqueue Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText(/Queue job #301 submitted\./i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Job #301/)).toBeInTheDocument();
    expect(screen.getByText(/status=running/)).toBeInTheDocument();
  });
});
