import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import OrchestratePage from "@/app/orchestrate/page";
import OrchestrationsPage from "@/app/orchestrations/page";

describe("orchestration workflow", () => {
  beforeEach(() => {
    vi.mocked(globalThis.fetch).mockReset();
    window.localStorage.clear();
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  function transientAbortError(): Error {
    return Object.assign(new Error("aborted"), { name: "AbortError" });
  }

  function unsignedEntitlementToken(tier: "free" | "pro" | "power", userId = "demo-user"): string {
    const payload = window
      .btoa(JSON.stringify({ tier, user_id: userId, exp: 1782059429 }))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replace(/=+$/, "");
    return `${payload}.signature`;
  }

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
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Approved for trusted DevOps workflow demo execution.",
            checkpoint_count: 4,
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
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Approved for trusted DevOps workflow demo execution.",
            checkpoint_count: 4,
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

  test("imports curated workflow templates and refreshes template list", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let listCalls = 0;
    let runBody: Record<string, unknown> | null = null;

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates/import/builtin")) {
        return new Response(
          JSON.stringify({
            imported: 13,
            updated: 0,
            skipped: 0,
            total: 13,
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/templates")) {
        listCalls += 1;
        const items =
          listCalls === 1
            ? []
            : [
                {
                  id: 501,
                  name: "AI-generated PR Release Gate",
                  description: "Gate an AI-authored pull request before CI/CD execution.",
                  steps: [
                    { step_name: "Normalize PR Change Request", agent_type: "planner", enabled: true },
                    { step_name: "Evaluate CI And Deployment Risk", agent_type: "analyzer", enabled: true },
                    { step_name: "Decide PR Release Gate", agent_type: "reviewer", enabled: true },
                  ],
                  tags: [
                    "pattern:maker-checker",
                    "tier:power",
                    "risk:high",
                    "approval:required",
                    "tool:ci-cd-release-gate",
                    "work-units:8",
                    "pr",
                    "ci-cd",
                    "release-gate",
                    "audit",
                  ],
                  policy: {
                    required_tier: "power",
                    risk_level: "high",
                    approval_required: true,
                    allowed_tool_scopes: ["ci-cd-release-gate"],
                    billable_work_units: 8,
                  },
                  enabled: true,
                  created_at: "2026-05-22T00:00:00Z",
                  updated_at: "2026-05-22T00:00:00Z",
                },
              ];
        return new Response(JSON.stringify(items), { status: 200 });
      }
      if (url.endsWith("/orchestrations/run")) {
        runBody = JSON.parse(String(init?.body ?? "{}"));
        return new Response(
          JSON.stringify({
            id: 501,
            status: "success",
            duration_ms: 111,
            entry_source: "web_ui",
            subscription_tier: "power",
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Approved for trusted DevOps workflow demo execution.",
            checkpoint_count: 4,
            summary: {
              conclusion: "Release gate approved and executed.",
              risks: [],
              next_actions: ["Capture release evidence."],
            },
            steps: [],
            created_at: "2026-05-22T00:00:00Z",
            updated_at: "2026-05-22T00:00:01Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);
    fireEvent.click(screen.getByRole("button", { name: "Import Curated Templates" }));

    await waitFor(() => {
      expect(screen.getByText("Curated templates imported: imported=13, updated=0.")).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: "AI-generated PR Release Gate" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Apply Existing Template"), { target: { value: "501" } });
    expect(screen.getByText("Pattern: Maker-checker · Tags: pr, ci-cd, release-gate, audit")).toBeInTheDocument();
    expect(
      screen.getAllByText("Policy: tier=power · risk high · approval required · work units 8 · tools ci-cd-release-gate")
        .length
    ).toBeGreaterThan(0);
    expect(screen.getByLabelText("Required Tier")).toHaveValue("power");
    expect(screen.getByLabelText("Risk Level")).toHaveValue("high");
    expect(screen.getByLabelText("Billable Work Units")).toHaveValue(8);
    expect(screen.getByLabelText("Allowed Tool Scopes")).toHaveValue("ci-cd-release-gate");
    fireEvent.click(screen.getByLabelText("Human Approval Confirmed"));
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));
    await waitFor(() => {
      expect(screen.getByText(/Run #501/i)).toBeInTheDocument();
    });
    expect(runBody).toMatchObject({
      template_id: 501,
      approval_confirmed: true,
      team_subject: "platform-team",
      requested_by: "sre-lead",
      approval_actor: "release-manager",
    });
  });

  test("loads manual billing entitlement and prevents pro users from running power templates", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    const proToken = unsignedEntitlementToken("pro");
    let runBody: Record<string, unknown> | null = null;
    let runHeaders: Record<string, string> | null = null;

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.includes("/monetization/entitlement?subject=demo-user")) {
        return new Response(
          JSON.stringify({
            token: proToken,
            tier: "pro",
            expires_at: "2026-06-21T00:00:00Z",
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
      }
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(
          JSON.stringify([
            {
              id: 801,
              name: "Kubernetes Path Readiness",
              description: "Power template.",
              steps: [
                { step_name: "Plan Cluster Gate", agent_type: "planner", enabled: true },
                { step_name: "Analyze Manifest Risk", agent_type: "analyzer", enabled: true },
                { step_name: "Review Deployment Path", agent_type: "reviewer", enabled: true },
              ],
              tags: ["pattern:handoff", "tier:power", "risk:high", "approval:required", "tool:kubernetes-readiness", "work-units:5"],
              policy: {
                required_tier: "power",
                risk_level: "high",
                approval_required: true,
                allowed_tool_scopes: ["kubernetes-readiness"],
                billable_work_units: 5,
              },
              enabled: true,
              created_at: "2026-05-22T00:00:00Z",
              updated_at: "2026-05-22T00:00:00Z",
            },
            {
              id: 802,
              name: "Production Incident Triage",
              description: "Pro template.",
              steps: [
                { step_name: "Plan Triage Window", agent_type: "planner", enabled: true },
                { step_name: "Analyze Incident Signals", agent_type: "analyzer", enabled: true },
                { step_name: "Review Containment Plan", agent_type: "reviewer", enabled: true },
              ],
              tags: ["pattern:sequential", "tier:pro", "risk:medium", "approval:none", "tool:read-only-diagnostics", "work-units:3"],
              policy: {
                required_tier: "pro",
                risk_level: "medium",
                approval_required: false,
                allowed_tool_scopes: ["read-only-diagnostics"],
                billable_work_units: 3,
              },
              enabled: true,
              created_at: "2026-05-22T00:00:00Z",
              updated_at: "2026-05-22T00:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/run")) {
        runBody = JSON.parse(String(init?.body ?? "{}"));
        runHeaders = (init?.headers ?? {}) as Record<string, string>;
        return new Response(
          JSON.stringify({
            id: 802,
            status: "success",
            duration_ms: 100,
            entry_source: "web_ui",
            subscription_tier: "pro",
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Approved for trusted DevOps workflow demo execution.",
            checkpoint_count: 4,
            summary: {
              conclusion: "Pro incident triage workflow completed.",
              risks: [],
              next_actions: ["Review history."],
            },
            steps: [],
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
      expect(screen.getByDisplayValue(proToken)).toBeInTheDocument();
    });
    expect(screen.getByText(/Current entitlement: PRO/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Apply Existing Template"), { target: { value: "801" } });
    expect(screen.getByText(/Current PRO entitlement cannot run this template/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Orchestration" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Use PRO-compatible template" }));
    expect(screen.queryByText(/Current PRO entitlement cannot run this template/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText(/Run #802/i)).toBeInTheDocument();
    });
    expect(runBody).toMatchObject({ template_id: 802 });
    expect(runHeaders).toMatchObject({ "X-Entitlement": proToken });
  });

  test("saves workflow templates with explicit commercial policy controls", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let createBody: Record<string, unknown> | null = null;

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/templates") && init?.method === "POST") {
        createBody = JSON.parse(String(init.body ?? "{}"));
        return new Response(
          JSON.stringify({
            id: 771,
            name: "Policy Authored Template",
            description: "Explicit commercial policy.",
            steps: [{ step_name: "Plan The Day", agent_type: "planner", enabled: true }],
            tags: ["tier:power", "risk:critical", "approval:required", "tool:server-deploy", "work-units:9"],
            policy: {
              required_tier: "power",
              risk_level: "critical",
              approval_required: true,
              allowed_tool_scopes: ["server-deploy"],
              billable_work_units: 9,
            },
            enabled: true,
            created_at: "2026-05-22T00:00:00Z",
            updated_at: "2026-05-22T00:00:00Z",
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);
    fireEvent.change(screen.getByLabelText("Template Name"), { target: { value: "Policy Authored Template" } });
    fireEvent.change(screen.getByLabelText("Required Tier"), { target: { value: "power" } });
    fireEvent.change(screen.getByLabelText("Risk Level"), { target: { value: "critical" } });
    fireEvent.change(screen.getByLabelText("Billable Work Units"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Allowed Tool Scopes"), { target: { value: "server-deploy" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Template" }));

    await waitFor(() => {
      expect(screen.getByText("Template 'Policy Authored Template' saved.")).toBeInTheDocument();
    });
    expect(createBody).toMatchObject({
      name: "Policy Authored Template",
      policy: {
        required_tier: "power",
        risk_level: "critical",
        approval_required: true,
        allowed_tool_scopes: ["server-deploy"],
        billable_work_units: 9,
      },
      enabled: true,
    });
  });

  test("loads a pilot scenario from the URL into release gate inputs", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    window.history.pushState({}, "", "/orchestrate?scenario=ci-flaky-release");

    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
      }
      if (url.endsWith("/orchestrations/pilot-scenarios")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "ci-flaky-release",
                name: "CI flaky release",
                description: "Intermittent CI failures require replay evidence.",
                expected_gate_behavior: "needs human review",
                required_tier: "power",
                approval_required: true,
                approval_confirmed: true,
                recommended_template_name: "AI-generated PR Release Gate",
                release_gate_input: {
                  pr_url: "https://github.com/example/platform/pull/1844",
                  pr_diff_summary: "Generated PR updates artifact publishing.",
                  ci_log_summary: "artifact upload timeout on first run; retry passed",
                  target_environment: "staging",
                  change_risk: "Medium-high risk because flaky CI can mask artifact integrity issues.",
                },
                daily_context: {
                  tasks: ["Triage flaky CI release gate", "Assign registry retry owner"],
                  meetings: ["Platform CI triage"],
                  blockers: ["Intermittent registry response needs owner"],
                  priorities: ["stabilize release evidence"],
                },
                technical_input: {
                  issue_description: "Artifact upload intermittently times out.",
                  errors: ["TimeoutError: registry upload did not respond"],
                  logs: "attempt 1 timeout\nattempt 2 passed",
                  code_snippets: ["curl --max-time 30 https://registry.example/upload"],
                },
                reflection_input: {
                  completed: ["CI timeline captured"],
                  unfinished: ["Registry owner validation"],
                  blockers: ["Missing owner for flaky dependency"],
                  mood_or_notes: "Buyer should see recoverability and checkpoint evidence.",
                },
                success_signal: "Run highlights needs-review decision with checkpointed retry evidence.",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(
          JSON.stringify([
            {
              id: 501,
              name: "AI-generated PR Release Gate",
              description: "Gate an AI-authored pull request before CI/CD execution.",
              steps: [
                { step_name: "Normalize PR Change Request", agent_type: "planner", enabled: true },
                { step_name: "Evaluate CI And Deployment Risk", agent_type: "analyzer", enabled: true },
                { step_name: "Decide PR Release Gate", agent_type: "reviewer", enabled: true },
              ],
              tags: ["pattern:maker-checker", "tier:power", "risk:high", "approval:required", "tool:ci-cd-release-gate", "work-units:8"],
              policy: {
                required_tier: "power",
                risk_level: "high",
                approval_required: true,
                allowed_tool_scopes: ["ci-cd-release-gate"],
                billable_work_units: 8,
              },
              enabled: true,
              created_at: "2026-05-22T00:00:00Z",
              updated_at: "2026-05-22T00:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);

    await waitFor(() => {
      expect(screen.getByText("Loaded pilot scenario: CI flaky release.")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Load Pilot Scenario")).toHaveValue("ci-flaky-release");
    expect(screen.getByLabelText("Apply Existing Template")).toHaveValue("501");
    expect(screen.getByDisplayValue("https://github.com/example/platform/pull/1844")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Artifact upload intermittently times out.")).toBeInTheDocument();
    expect(screen.getByLabelText("Human Approval Confirmed")).toBeChecked();

    window.history.pushState({}, "", "/");
  });

  test("guides missing approval pilot scenario through expected block and rerun", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    const powerToken = unsignedEntitlementToken("power");
    window.localStorage.setItem("entitlement_token", powerToken);
    window.history.pushState({}, "", "/orchestrate?scenario=missing-approval");
    let runCalls = 0;

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
      }
      if (url.endsWith("/orchestrations/pilot-scenarios")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "missing-approval",
                name: "Missing approval",
                description: "Power gate blocks a risky release until approval metadata is confirmed.",
                expected_gate_behavior: "block",
                required_tier: "power",
                approval_required: true,
                approval_confirmed: false,
                recommended_template_name: "AI-generated PR Release Gate",
                release_gate_input: {
                  pr_url: "https://github.com/example/platform/pull/1845",
                  pr_diff_summary: "Generated PR changes production deploy permissions.",
                  ci_log_summary: "tests passed; production dry-run skipped until release manager approval",
                  target_environment: "production",
                  change_risk: "High-risk production change lacks approval confirmation.",
                },
                daily_context: {
                  tasks: ["Attempt approval-gated release"],
                  meetings: [],
                  blockers: ["Approval not confirmed"],
                  priorities: ["prove approval block"],
                },
                technical_input: {
                  issue_description: "High-risk release must be blocked because approval is not confirmed.",
                  errors: ["Policy gate: approval not confirmed"],
                  logs: "tests passed\napproval pending",
                  code_snippets: ["gh pr view 1845 --json reviews"],
                },
                reflection_input: {
                  completed: ["Policy block captured"],
                  unfinished: ["Release manager approval"],
                  blockers: ["Approval confirmation missing"],
                  mood_or_notes: "Buyer should see the policy gate block before approval.",
                },
                success_signal: "Initial run returns 409 until approval is explicitly confirmed.",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/templates")) {
        return new Response(
          JSON.stringify([
            {
              id: 501,
              name: "AI-generated PR Release Gate",
              description: "Gate an AI-authored pull request before CI/CD execution.",
              steps: [
                { step_name: "Normalize PR Change Request", agent_type: "planner", enabled: true },
                { step_name: "Evaluate CI And Deployment Risk", agent_type: "analyzer", enabled: true },
                { step_name: "Decide PR Release Gate", agent_type: "reviewer", enabled: true },
              ],
              tags: ["pattern:maker-checker", "tier:power", "risk:high", "approval:required", "tool:ci-cd-release-gate", "work-units:8"],
              policy: {
                required_tier: "power",
                risk_level: "high",
                approval_required: true,
                allowed_tool_scopes: ["ci-cd-release-gate"],
                billable_work_units: 8,
              },
              enabled: true,
              created_at: "2026-05-22T00:00:00Z",
              updated_at: "2026-05-22T00:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/run")) {
        runCalls += 1;
        const body = JSON.parse(String(init?.body ?? "{}"));
        if (!body.approval_confirmed) {
          return new Response(
            JSON.stringify({
              detail: {
                code: "approval_required",
                message: "Template 'AI-generated PR Release Gate' requires explicit human approval.",
              },
            }),
            { status: 409 }
          );
        }
        return new Response(
          JSON.stringify({
            id: 901,
            status: "success",
            duration_ms: 100,
            entry_source: "pilot_scenario",
            pilot_scenario_id: "missing-approval",
            subscription_tier: "power",
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Pilot scenario: Missing approval.",
            checkpoint_count: 4,
            summary: {
              conclusion: "Release gate completed after approval confirmation.",
              risks: [],
              next_actions: ["Review closeout."],
            },
            steps: [],
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
      expect(screen.getByText("Loaded pilot scenario: Missing approval.")).toBeInTheDocument();
    });
    expect(screen.getByText(/Expected policy block/)).toBeInTheDocument();
    expect(screen.getByLabelText("Human Approval Confirmed")).not.toBeChecked();

    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));
    await waitFor(() => {
      expect(screen.getByText(/expected policy block for the Missing approval pilot scenario/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Human Approval Confirmed"));
    fireEvent.click(screen.getByRole("button", { name: "Run Orchestration" }));

    await waitFor(() => {
      expect(screen.getByText(/Run #901/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Back To Tutorial" })).toHaveAttribute("href", "/tutorial");
    expect(screen.getByRole("link", { name: "Review Pilot Closeout" })).toHaveAttribute("href", "/monetization");
    expect(runCalls).toBe(2);

    window.history.pushState({}, "", "/");
  });

  test("recovers workflow template loading after a transient browser timeout", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let templateCalls = 0;

    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/orchestrations/entitlement/bootstrap")) {
        return new Response(JSON.stringify({ detail: "Not found." }), { status: 404 });
      }
      if (url.endsWith("/orchestrations/templates")) {
        templateCalls += 1;
        if (templateCalls === 1) {
          throw transientAbortError();
        }
        return new Response(
          JSON.stringify([
            {
              id: 701,
              name: "Transient Recovery Template",
              description: "Template list should recover after one aborted browser request.",
              steps: [{ step_name: "Recover Template Load", agent_type: "planner", enabled: true }],
              tags: ["pattern:sequential", "tier:pro", "risk:low", "approval:none", "tool:none", "work-units:1"],
              policy: {
                required_tier: "pro",
                risk_level: "low",
                approval_required: false,
                allowed_tool_scopes: ["none"],
                billable_work_units: 1,
              },
              enabled: true,
              created_at: "2026-05-22T00:00:00Z",
              updated_at: "2026-05-22T00:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestratePage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Transient Recovery Template" })).toBeInTheDocument();
    });
    expect(templateCalls).toBe(2);
    expect(screen.queryByText("Request timed out. Please retry.")).not.toBeInTheDocument();
  });

  test("runs orchestration then verifies replay in history page", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    const createdRun = {
      id: 909,
      status: "success",
      duration_ms: 88,
      entry_source: "web_ui",
      subscription_tier: "pro",
      team_subject: "platform-team",
      requested_by: "sre-lead",
      approval_actor: "release-manager",
      approval_note: "Approved for trusted DevOps workflow demo execution.",
      checkpoint_count: 3,
      billable_work_units: 8,
      policy_gate: {
        template_id: 501,
        template_name: "AI-generated PR Release Gate",
        required_tier: "power",
        risk_level: "high",
        approval_required: true,
        approval_confirmed: true,
        allowed_tool_scopes: ["ci-cd-release-gate"],
        billable_work_units: 8,
        decision: "needs human review",
      },
      roi_evidence: {
        review_time_saved_minutes: 63,
        audit_time_saved_minutes: 50,
        blocked_risk_count: 1,
        blocked_risk_value_usd: 5000,
        estimated_customer_value_usd: 5283,
        billable_work_units: 8,
        assumptions: [
          "Engineering review time is estimated at 6 minutes per billable work unit plus approval overhead.",
          "Audit time is estimated from work units and checkpoint-ready evidence.",
        ],
      },
      summary: {
        conclusion: "Planner created a deployable orchestration checklist.",
        risks: ["Blocked risk: generated PR change can affect production without release ownership."],
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
        return new Response(
          JSON.stringify({
            items: [
              {
                ...createdRun,
                ledger_integrity: {
                  entity_type: "orchestration",
                  entity_id: "909",
                  integrity_status: "valid",
                  event_count: 3,
                },
              },
            ],
          }),
          { status: 200 }
        );
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
      if (url.endsWith("/orchestrations/909/checkpoints")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 1,
                checkpoint_uid: "checkpoint-1",
                entity_type: "orchestration",
                entity_id: "909",
                orchestration_id: 909,
                queue_job_id: null,
                checkpoint_type: "orchestration.accepted",
                step_name: "",
                step_index: null,
                status: "running",
                payload: { team_subject: "platform-team" },
                payload_sha256: "abc",
                created_by: "sre-lead",
                created_at: "2026-05-21T00:00:00Z",
                integrity_status: "valid",
                integrity_error: "",
              },
              {
                id: 2,
                checkpoint_uid: "checkpoint-2",
                entity_type: "orchestration",
                entity_id: "909",
                orchestration_id: 909,
                queue_job_id: null,
                checkpoint_type: "step.success",
                step_name: "Plan The Day",
                step_index: 1,
                status: "success",
                payload: { step_name: "Plan The Day" },
                payload_sha256: "def",
                created_by: "sre-lead",
                created_at: "2026-05-21T00:00:01Z",
                integrity_status: "valid",
                integrity_error: "",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/909/evidence")) {
        return new Response(
          JSON.stringify({
            orchestration_id: 909,
            generated_at: "2026-05-21T00:00:02Z",
            format: "markdown",
            markdown:
              "# Orchestration Evidence Export #909\n\n## PR / CI Context\n- PR URL: https://github.com/example/platform/pull/1842\n\n## ROI Evidence\n- Estimated customer value: $5283\n",
            data: {},
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
      expect(screen.getByRole("heading", { name: "Run #909" })).toBeInTheDocument();
    });
    expect(screen.getByText("success · pro · 88ms")).toBeInTheDocument();
    expect(screen.getByText("Planner created a deployable orchestration checklist.")).toBeInTheDocument();
    expect(screen.getByText("Planner produced launch validation steps.")).toBeInTheDocument();
    expect(screen.getByText(/History Ledger: valid · 3 event\(s\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Team: platform-team · requested by sre-lead · approved by release-manager/i)).toBeInTheDocument();
    expect(screen.getByText(/AI-generated PR Release Gate · tier=power · risk high/i)).toBeInTheDocument();
    expect(screen.getByText(/decision=needs human review/i)).toBeInTheDocument();
    expect(screen.getByText("Work Units: 8")).toBeInTheDocument();
    expect(screen.getByText(/Blocked risk: generated PR change can affect production/i)).toBeInTheDocument();
    expect(screen.getByText("ROI Evidence")).toBeInTheDocument();
    expect(screen.getByText(/\$5,283 estimated value · 113m saved/i)).toBeInTheDocument();
    expect(screen.getByText(/blocked risk 1 · risk value \$5,000 · work units 8/i)).toBeInTheDocument();
    expect(screen.getByText(/Checkpoints: 3/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verify History Ledger" }));
    await waitFor(() => {
      expect(screen.getByText(/History Ledger: valid · 3 event\(s\)/i)).toBeInTheDocument();
    });
    expect(screen.getByText("orchestration.accepted")).toBeInTheDocument();
    expect(screen.getByText(/hash abc/i)).toBeInTheDocument();
    expect(screen.getByText("Plan The Day · success")).toBeInTheDocument();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    fireEvent.click(screen.getByRole("button", { name: "Export Evidence" }));
    await waitFor(() => {
      expect(screen.getByText("Evidence Export")).toBeInTheDocument();
    });
    expect(screen.getByText(/Orchestration Evidence Export #909/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy Markdown" }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Orchestration Evidence Export #909"));
    });
    expect(screen.getByRole("button", { name: "Download Markdown" })).toBeInTheDocument();
  });

  test("renders orchestration history with filters", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let job402Canceled = false;
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
        job402Canceled = true;
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
        if (job402Canceled) {
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
      expect(screen.getByRole("heading", { name: "Run #202" })).toBeInTheDocument();
    });
    expect(screen.getByText("partial_success · pro · 230ms")).toBeInTheDocument();
    expect(screen.getByText("Analyzer requested more technical evidence.")).toBeInTheDocument();
    expect(screen.getByText(/Fallback: Gather one concrete error signal/i)).toBeInTheDocument();
    expect(screen.getByText(/Queue Job List/i)).toBeInTheDocument();
    expect(screen.getAllByText(/cancel_requested=true/i).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getAllByText("Job #401").length).toBeGreaterThan(0);
      expect(screen.getByText("latest status=failed")).toBeInTheDocument();
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
      expect(screen.getByText("latest status=canceled")).toBeInTheDocument();
    });
  });

  test("recovers orchestration and queue history after transient browser timeouts", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    let historyCalls = 0;
    let queueHistoryCalls = 0;

    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/orchestrations/history")) {
        historyCalls += 1;
        if (historyCalls === 1) {
          throw transientAbortError();
        }
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 808,
                status: "success",
                duration_ms: 75,
                entry_source: "web_ui",
                subscription_tier: "pro",
                team_subject: "platform-team",
                requested_by: "sre-lead",
                approval_actor: "release-manager",
                approval_note: "Recovered from transient timeout.",
                checkpoint_count: 4,
                ledger_integrity: {
                  entity_type: "orchestration",
                  entity_id: "808",
                  integrity_status: "valid",
                  event_count: 4,
                },
                summary: {
                  conclusion: "History recovered after retry.",
                  risks: [],
                  next_actions: ["Keep the page usable after a transient network abort."],
                },
                steps: [
                  {
                    id: 31,
                    step_name: "Plan The Day",
                    agent_type: "planner",
                    status: "success",
                    input_summary: "{}",
                    output_summary: "Recovered history item.",
                    audit: {
                      conclusion: "Recovered history item.",
                      evidence: "The GET request retried once.",
                      risk: "Without retry, the page would stay on timeout.",
                      next_action: "Render replay after recovery.",
                    },
                    fallback_action: "",
                    started_at: "2026-05-22T00:00:00Z",
                    finished_at: "2026-05-22T00:00:01Z",
                    duration_ms: 75,
                  },
                ],
                created_at: "2026-05-22T00:00:00Z",
                updated_at: "2026-05-22T00:00:01Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.includes("/orchestrations/queue/history")) {
        queueHistoryCalls += 1;
        if (queueHistoryCalls === 1) {
          throw transientAbortError();
        }
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 811,
                status: "succeeded",
                attempts: 1,
                max_attempts: 3,
                cancel_requested: false,
                orchestration_id: 808,
                team_subject: "platform-team",
                requested_by: "sre-lead",
                approval_actor: "release-manager",
                approval_note: "Recovered from transient timeout.",
                error_message: "",
                created_at: "2026-05-22T00:00:00Z",
                updated_at: "2026-05-22T00:00:01Z",
                events: [],
                checkpoints: [],
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/orchestrations/queue/811")) {
        return new Response(
          JSON.stringify({
            id: 811,
            status: "succeeded",
            attempts: 1,
            max_attempts: 3,
            cancel_requested: false,
            orchestration_id: 808,
            team_subject: "platform-team",
            requested_by: "sre-lead",
            approval_actor: "release-manager",
            approval_note: "Recovered from transient timeout.",
            error_message: "",
            created_at: "2026-05-22T00:00:00Z",
            updated_at: "2026-05-22T00:00:01Z",
            events: [],
            checkpoints: [],
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ items: [] }), { status: 200 });
    });

    render(<OrchestrationsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Run #808" })).toBeInTheDocument();
      expect(screen.getByText("Job #811")).toBeInTheDocument();
    });
    expect(historyCalls).toBe(2);
    expect(queueHistoryCalls).toBe(2);
    expect(screen.queryByText("Request timed out. Please retry.")).not.toBeInTheDocument();
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
