import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import TechnicalAnalysisPage from "@/app/technical-analysis/page";

describe("technical analysis workflow", () => {
  test("submits issue and renders structured analysis", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();

      if (url.endsWith("/analysis/history")) {
        return new Response(JSON.stringify({ items: [] }), { status: 200 });
      }

      if (url.endsWith("/analysis/technical")) {
        return new Response(
          JSON.stringify({
            id: 30,
            analysis_date: "2026-04-16",
            input: {
              issue_description: "Deploy stage timeout on artifact upload",
              errors: ["TimeoutError: upload call exceeded 30s"],
              logs: "deploy start\nupload artifact\ntimeout\njob failed",
              code_snippets: ["curl --max-time 30 https://registry/api/upload"],
            },
            output: {
              problem_statement: "Observed technical issue: Deploy stage timeout on artifact upload",
              likely_causes: ["Dependency response exceeded timeout budget under current retry/backoff settings."],
              validation_steps: [
                "Reproduce once with stable input and confirm the same symptom: 'Deploy stage timeout on artifact upload'.",
              ],
              fix_options: [
                "Increase client timeout modestly and add bounded retries with jitter while tracking p95 latency.",
              ],
              risks: ["Masking root latency by only increasing timeout can worsen queueing under peak load."],
              follow_up_tasks: [
                "Document incident note with symptom and timeline: 'Deploy stage timeout on artifact upload'.",
              ],
            },
            created_at: "2026-04-16T08:00:00Z",
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<TechnicalAnalysisPage />);

    fireEvent.change(screen.getByLabelText("Issue Description"), {
      target: { value: "Deploy stage timeout on artifact upload" },
    });
    fireEvent.change(screen.getByLabelText("Errors (one per line)"), {
      target: { value: "TimeoutError: upload call exceeded 30s" },
    });
    fireEvent.change(screen.getByLabelText("Logs"), {
      target: { value: "deploy start\nupload artifact\ntimeout\njob failed" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Analyze Technical Issue" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Generated Analysis" })).toBeInTheDocument();
    });
    expect(screen.getByText("Technical analysis generated and saved.")).toBeInTheDocument();
    expect(
      screen.getByText("Dependency response exceeded timeout budget under current retry/backoff settings.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Masking root latency by only increasing timeout can worsen queueing under peak load.")
    ).toBeInTheDocument();
  });

  test("loads and shows technical analysis history", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();

      if (url.endsWith("/analysis/history")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 31,
                analysis_date: "2026-04-15",
                input: {
                  issue_description: "Image push permission denied",
                  errors: ["permission denied for artifact upload"],
                  logs: "",
                  code_snippets: [],
                },
                output: {
                  problem_statement: "Observed technical issue: Image push permission denied",
                  likely_causes: ["Credential, token scope, or IAM policy does not permit the failing operation."],
                  validation_steps: ["step"],
                  fix_options: ["Align service account/role permissions with required API actions and rotate stale tokens."],
                  risks: ["Over-broad permission updates can create security exposure."],
                  follow_up_tasks: ["task"],
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

    render(<TechnicalAnalysisPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Analysis History" })).toBeInTheDocument();
    });
    expect(screen.getByText("2026-04-15")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Observed technical issue: Image push permission denied"
      )
    ).toBeInTheDocument();
  });
});
