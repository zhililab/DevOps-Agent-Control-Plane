import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import OrchestratePage from "@/app/orchestrate/page";
import OrchestrationsPage from "@/app/orchestrations/page";

describe("orchestration workflow", () => {
  beforeEach(() => {
    vi.mocked(globalThis.fetch).mockReset();
    window.localStorage.clear();
  });

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
    expect(screen.getByRole("link", { name: "View Orchestration History" })).toHaveAttribute(
      "href",
      "/orchestrations"
    );
    const runCall = fetchMock.mock.calls.find(([input]) => input.toString().endsWith("/orchestrations/run"));
    expect(runCall?.[1]?.headers).not.toHaveProperty("X-Subscription-Tier");
  });

  test("refreshes stale entitlement token and retries orchestration once", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    const runHeaders: Record<string, string>[] = [];
    let bootstrapCalls = 0;
    window.localStorage.setItem("entitlement_token", "stale-token");

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        bootstrapCalls += 1;
        if (bootstrapCalls === 1) {
          return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
        }
        return new Response(
          JSON.stringify({
            token: "fresh-token",
            tier: "pro",
            expires_at: "2026-05-22T01:00:00Z",
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/run")) {
        runHeaders.push((init?.headers ?? {}) as Record<string, string>);
        if (runHeaders.length === 1) {
          return new Response(JSON.stringify({ detail: "Invalid entitlement signature." }), { status: 401 });
        }
        return new Response(
          JSON.stringify({
            id: 102,
            status: "success",
            duration_ms: 90,
            entry_source: "web_ui",
            subscription_tier: "pro",
            summary: {
              conclusion: "Recovered after refreshing stale entitlement.",
              risks: [],
              next_actions: ["Keep replay visible."],
            },
            steps: [
              {
                id: 2,
                step_name: "Plan The Day",
                agent_type: "planner",
                status: "success",
                input_summary: "{}",
                output_summary: "Planner completed after token refresh.",
                audit: {
                  conclusion: "Planner completed after token refresh.",
                  evidence: "Signed entitlement was refreshed.",
                  risk: "Old browser tokens can become stale after deploys.",
                  next_action: "Continue with refreshed entitlement.",
                },
                fallback_action: "",
                started_at: "2026-05-22T00:00:00Z",
                finished_at: "2026-05-22T00:00:01Z",
                duration_ms: 90,
              },
            ],
            created_at: "2026-05-22T00:00:00Z",
            updated_at: "2026-05-22T00:00:01Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);

    await waitFor(() => {
      expect(bootstrapCalls).toBe(1);
    });
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText(/Run #102/i)).toBeInTheDocument();
    });
    expect(screen.queryByText("Invalid entitlement signature.")).not.toBeInTheDocument();
    expect(runHeaders).toHaveLength(2);
    expect(runHeaders[0]).toMatchObject({ "X-Entitlement": "stale-token" });
    expect(runHeaders[1]).toMatchObject({ "X-Entitlement": "fresh-token" });
    expect(runHeaders[1]).not.toHaveProperty("X-Subscription-Tier");
    expect(window.localStorage.getItem("entitlement_token")).toBe("fresh-token");
  });

  test("runs orchestration then verifies replay in history page", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    const createdRun = {
      id: 909,
      status: "success",
      duration_ms: 88,
      entry_source: "web_ui",
      subscription_tier: "pro",
      summary: {
        conclusion: "Planner created a deployable orchestration checklist.",
        risks: ["Deployment evidence still needs capture."],
        next_actions: ["Open orchestration history and verify replay."],
      },
      steps: [
        {
          id: 91,
          step_name: "Plan The Day",
          agent_type: "planner",
          status: "success",
          input_summary: "{}",
          output_summary: "Planner produced launch validation steps.",
          audit: {
            conclusion: "Planner produced launch validation steps.",
            evidence: "Input contained release closeout context.",
            risk: "Skipping history verification weakens auditability.",
            next_action: "Confirm the run appears in history.",
          },
          fallback_action: "",
          started_at: "2026-05-21T00:00:00Z",
          finished_at: "2026-05-21T00:00:01Z",
          duration_ms: 88,
        },
      ],
      created_at: "2026-05-21T00:00:00Z",
      updated_at: "2026-05-21T00:00:01Z",
    };

    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith("/orchestrations/run")) {
        return new Response(JSON.stringify(createdRun), { status: 200 });
      }
      if (url.includes("/orchestrations/history")) {
        return new Response(JSON.stringify({ items: [createdRun] }), { status: 200 });
      }
      if (url.includes("/orchestrations/queue/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }
      if (url.endsWith("/orchestrations/909/history-events")) {
        return new Response(
          JSON.stringify({
            entity_type: "orchestration",
            entity_id: "909",
            integrity_status: "valid",
            event_count: 3,
            events: [],
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    const { unmount } = render(<OrchestratePage />);
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText(/Run #909/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "View Orchestration History" })).toHaveAttribute(
      "href",
      "/orchestrations"
    );

    unmount();
    render(<OrchestrationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Run #909 · success · pro")).toBeInTheDocument();
    });
    expect(screen.getByText("Planner created a deployable orchestration checklist.")).toBeInTheDocument();
    expect(screen.getByText("Planner produced launch validation steps.")).toBeInTheDocument();
    expect(screen.getByText(/History Ledger: not checked/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verify History Ledger" }));
    await waitFor(() => {
      expect(screen.getByText(/History Ledger: valid · 3 event\(s\)/i)).toBeInTheDocument();
    });
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
      if (url.includes("/orchestrations/queue/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 401,
                status: "failed",
                attempts: 2,
                max_attempts: 3,
                cancel_requested: true,
                orchestration_id: 202,
                error_message: "Analyzer timeout",
                created_at: "2026-04-23T00:00:00Z",
                updated_at: "2026-04-23T00:00:10Z",
              },
              {
                id: 402,
                status: "running",
                attempts: 1,
                max_attempts: 3,
                cancel_requested: false,
                orchestration_id: null,
                error_message: "",
                created_at: "2026-04-23T00:01:00Z",
                updated_at: "2026-04-23T00:01:10Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/401/retry")) {
        return new Response(
          JSON.stringify({
            job_id: 401,
            status: "queued",
            attempts: 2,
            max_attempts: 3,
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/402/cancel")) {
        return new Response(
          JSON.stringify({
            id: 402,
            status: "canceled",
            attempts: 1,
            max_attempts: 3,
            cancel_requested: true,
            orchestration_id: null,
            error_message: "",
            created_at: "2026-04-23T00:01:00Z",
            updated_at: "2026-04-23T00:01:20Z",
            events: [
              {
                id: 4,
                queue_job_id: 402,
                event_type: "cancel_requested",
                status: "canceled",
                detail: "Cancel requested while job is running.",
                created_at: "2026-04-23T00:01:20Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/401")) {
        return new Response(
          JSON.stringify({
            id: 401,
            status: "failed",
            attempts: 2,
            max_attempts: 3,
            cancel_requested: true,
            orchestration_id: 202,
            error_message: "Analyzer timeout",
            created_at: "2026-04-23T00:00:00Z",
            updated_at: "2026-04-23T00:00:10Z",
            events: [
              {
                id: 1,
                queue_job_id: 401,
                event_type: "queued",
                status: "queued",
                detail: "Job accepted and queued.",
                created_at: "2026-04-23T00:00:00Z",
              },
              {
                id: 2,
                queue_job_id: 401,
                event_type: "started",
                status: "running",
                detail: "Execution started (attempt 1/3).",
                created_at: "2026-04-23T00:00:02Z",
              },
              {
                id: 3,
                queue_job_id: 401,
                event_type: "failed",
                status: "failed",
                detail: "Execution failed: Analyzer timeout",
                created_at: "2026-04-23T00:00:10Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/402")) {
        return new Response(
          JSON.stringify({
            id: 402,
            status: "running",
            attempts: 1,
            max_attempts: 3,
            cancel_requested: false,
            orchestration_id: null,
            error_message: "",
            created_at: "2026-04-23T00:01:00Z",
            updated_at: "2026-04-23T00:01:10Z",
            events: [
              {
                id: 4,
                queue_job_id: 402,
                event_type: "started",
                status: "running",
                detail: "Execution started (attempt 1/3).",
                created_at: "2026-04-23T00:01:10Z",
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
    expect(screen.getByText(/Queue Job List/i)).toBeInTheDocument();
    expect(screen.getAllByText(/cancel_requested=true/i).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(
        screen.getByText((content) => content.replace(/\s+/g, " ").trim() === "Job #401 · latest status=failed")
      ).toBeInTheDocument();
      expect(screen.getByText(/Observed queue events/i)).toBeInTheDocument();
      expect(screen.getByText("Execution failed: Analyzer timeout")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Retry Job" })[0]);
    await waitFor(() => {
      expect(screen.getByText("Queue job #401 retry requested.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Cancel Job" })[1]);
    await waitFor(() => {
      expect(screen.getByText("Queue job #402 cancel request accepted.")).toBeInTheDocument();
      expect(screen.getByText(/Job #402 · latest status=canceled/i)).toBeInTheDocument();
    });
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
