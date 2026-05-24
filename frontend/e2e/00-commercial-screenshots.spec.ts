import { expect, test } from "@playwright/test";

const commercialMetricsPayload = {
  window_days: 7,
  generated_at: "2026-05-22T00:00:00Z",
  subject: null,
  subscription_summary: {
    active_subjects: 2,
    profile_count: 3,
    tier_distribution: { free: 1, pro: 1, power: 1 },
    status_distribution: { inactive: 0, active: 2, past_due: 0, canceled: 1 },
  },
  usage_summary: {
    workflow_runs_used: 18,
    workflow_runs_limit: 2300,
    queued_runs_used: 5,
    queued_runs_limit: 2300,
    usage_subjects: 2,
  },
  plan_usage: {
    workflow_runs_used: 18,
    workflow_runs_limit: 2300,
    queued_runs_used: 5,
    queued_runs_limit: 2300,
    period_start: "2026-05-01",
    period_end: "2026-05-31",
  },
  commercial_events: [
    { action: "checkout completed", count: 2 },
    { action: "tier changed", count: 1 },
  ],
  policy_blocks: { approval_required: 2, upgrade_required: 3, quota_exceeded: 0, total: 5 },
  billable_work_units: { total: 21, audited_workflows: 6, average_per_run: 3.5 },
  roi_summary: {
    runs_with_roi: 6,
    estimated_customer_value_usd: 16800,
    review_time_saved_minutes: 180,
    audit_time_saved_minutes: 120,
    blocked_risk_count: 3,
    blocked_risk_value_usd: 15000,
    billable_work_units: 21,
    work_units_by_template: [
      {
        template_id: 7,
        template_name: "Power Release Gate",
        runs: 3,
        billable_work_units: 12,
        estimated_customer_value_usd: 9800,
      },
    ],
  },
  top_templates: [
    {
      template_id: 7,
      template_name: "Power Release Gate",
      runs: 3,
      billable_work_units: 12,
      required_tier: "power",
      risk_level: "high",
      approval_required: true,
    },
    {
      template_id: 3,
      template_name: "Incident Triage",
      runs: 2,
      billable_work_units: 6,
      required_tier: "pro",
      risk_level: "medium",
      approval_required: false,
    },
  ],
  trend: [
    { date: "2026-05-16", billable_work_units: 1, audited_workflows: 1, policy_blocks: 0 },
    { date: "2026-05-17", billable_work_units: 2, audited_workflows: 1, policy_blocks: 0 },
    { date: "2026-05-18", billable_work_units: 4, audited_workflows: 1, policy_blocks: 1 },
    { date: "2026-05-19", billable_work_units: 3, audited_workflows: 1, policy_blocks: 1 },
    { date: "2026-05-20", billable_work_units: 5, audited_workflows: 1, policy_blocks: 1 },
    { date: "2026-05-21", billable_work_units: 6, audited_workflows: 1, policy_blocks: 2 },
  ],
  anomaly_hints: [
    {
      code: "upgrade_blocks_rising",
      severity: "warning",
      message: "Upgrade blocks increased; Power plan education should be visible.",
    },
  ],
};

const workflowTemplatePayload = [
  {
    id: 7,
    name: "Power Release Gate",
    description: "Approval-gated release workflow for a small DevOps team.",
    steps: [
      { step_name: "Plan release", agent_type: "planner", enabled: true },
      { step_name: "Analyze deployment risk", agent_type: "analyzer", enabled: true },
      { step_name: "Review approval evidence", agent_type: "reviewer", enabled: true },
    ],
    tags: ["devops", "release"],
    policy: {
      required_tier: "power",
      risk_level: "high",
      approval_required: true,
      allowed_tool_scopes: ["read:deployments", "write:knowledge"],
      billable_work_units: 4,
    },
    enabled: true,
    created_at: "2026-05-22T00:00:00Z",
    updated_at: "2026-05-22T00:00:00Z",
  },
];

const orchestrationHistoryPayload = {
  items: [
    {
      id: 41,
      status: "success",
      duration_ms: 1450,
      entry_source: "demo",
      subscription_tier: "power",
      team_subject: "platform-team",
      requested_by: "sre-lead",
      approval_actor: "release-manager",
      approval_note: "Approved for trusted DevOps workflow demo execution.",
      summary: {
        conclusion: "Release gate passed with replayable evidence.",
        risks: ["Registry retry policy still needs owner confirmation."],
        next_actions: ["Ship with Power approval evidence attached."],
      },
      steps: [
        {
          id: 91,
          step_name: "Plan release",
          agent_type: "planner",
          status: "success",
          input_summary: "Release gate and incident context.",
          output_summary: "Planner prioritized the release checklist.",
          audit: {
            conclusion: "Planner created a deterministic release order.",
            evidence: "Input contained 2 tasks and 1 blocker.",
            risk: "Owner validation remains open.",
            next_action: "Attach approval note before deploy.",
          },
          fallback_action: "",
          started_at: "2026-05-22T00:00:00Z",
          finished_at: "2026-05-22T00:00:01Z",
          duration_ms: 500,
        },
      ],
      ledger_integrity: { entity_type: "orchestration", entity_id: "41", integrity_status: "valid", event_count: 6 },
      checkpoint_count: 5,
      created_at: "2026-05-22T00:00:00Z",
      updated_at: "2026-05-22T00:00:01Z",
    },
  ],
};

const queueHistoryPayload = {
  items: [
    {
      id: 12,
      status: "succeeded",
      attempts: 1,
      max_attempts: 3,
      cancel_requested: false,
      orchestration_id: 41,
      team_subject: "platform-team",
      requested_by: "sre-lead",
      approval_actor: "release-manager",
      approval_note: "Approved for trusted DevOps workflow demo execution.",
      error_message: "",
      created_at: "2026-05-22T00:00:00Z",
      updated_at: "2026-05-22T00:00:01Z",
    },
  ],
};

async function installStableApiRoutes(page: import("@playwright/test").Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const apiPath = url.pathname.replace(/^\/api/, "");

    const fulfillJson = (payload: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });

    if (apiPath === "/plans/history" || apiPath === "/reflections/history" || apiPath === "/analysis/history") {
      return fulfillJson({ items: [] });
    }
    if (apiPath === "/orchestrations/metrics") {
      return fulfillJson({
        period_days: Number(url.searchParams.get("days") ?? 7),
        total_runs: 6,
        weekly_active_orchestrations: 4,
        partial_success_rate: 0.17,
        average_duration_ms: 1450,
        billable_work_units: 21,
        successful_audited_workflows: 6,
        approval_required_blocks: 2,
        template_policy_upgrade_blocks: 3,
        approved_runs: 5,
        checkpointed_runs: 6,
        failed_jobs_needing_owner: 1,
      });
    }
    if (apiPath === "/orchestrations/history") {
      return fulfillJson(orchestrationHistoryPayload);
    }
    if (apiPath === "/orchestrations/queue/history") {
      return fulfillJson(queueHistoryPayload);
    }
    if (/^\/orchestrations\/queue\/\d+$/.test(apiPath)) {
      return fulfillJson({
        ...queueHistoryPayload.items[0],
        events: [
          {
            id: 31,
            queue_job_id: 12,
            event_type: "queued",
            status: "queued",
            detail: "Job accepted for Power release gate execution.",
            created_at: "2026-05-22T00:00:00Z",
          },
          {
            id: 32,
            queue_job_id: 12,
            event_type: "succeeded",
            status: "succeeded",
            detail: "Workflow completed with audit evidence.",
            created_at: "2026-05-22T00:00:01Z",
          },
        ],
        checkpoints: [
          {
            id: 44,
            checkpoint_uid: "screenshot-checkpoint",
            entity_type: "orchestration",
            entity_id: "41",
            orchestration_id: 41,
            queue_job_id: 12,
            checkpoint_type: "queue.succeeded",
            step_name: "Review approval evidence",
            step_index: 2,
            status: "succeeded",
            payload: { status: "succeeded" },
            payload_sha256: "stable",
            created_by: "screenshot",
            created_at: "2026-05-22T00:00:01Z",
            integrity_status: "valid",
            integrity_error: "",
          },
        ],
      });
    }
    if (apiPath === "/orchestrations/entitlement/bootstrap") {
      return fulfillJson({
        token: "stable-screenshot-token",
        tier: "pro",
        expires_at: "2026-06-21T00:00:00Z",
      });
    }
    if (apiPath === "/orchestrations/templates") {
      return fulfillJson(workflowTemplatePayload);
    }
    if (apiPath === "/observability/monetization") {
      return fulfillJson({
        period_days: Number(url.searchParams.get("days") ?? 7),
        kpis: {
          total_revenue_usd: 1856,
          paid_runs: 18,
          conversion_rate: 0.42,
          failed_payment_rate: 0,
        },
        trend: [
          { date: "2026-05-20", revenue_usd: 180, paid_runs: 4, conversion_rate: 0.32 },
          { date: "2026-05-21", revenue_usd: 420, paid_runs: 7, conversion_rate: 0.38 },
          { date: "2026-05-22", revenue_usd: 560, paid_runs: 7, conversion_rate: 0.42 },
        ],
        health: {
          status: "healthy",
          summary: "Commercial control-plane metrics are within expected bounds.",
          incidents: [],
        },
      });
    }
    if (apiPath === "/monetization/profile") {
      return fulfillJson({ profile: null });
    }
    if (apiPath === "/monetization/usage") {
      return fulfillJson({ counters: [] });
    }
    if (apiPath === "/monetization/events") {
      return fulfillJson({ events: [] });
    }
    if (apiPath === "/monetization/entitlement") {
      return fulfillJson({
        token: "eyJ0aWVyIjoicHJvIiwidXNlcl9pZCI6ImRlbW8tdXNlciIsImV4cCI6MTc4MjA1OTQyOX0.signature",
        tier: "pro",
        expires_at: "2026-06-21T00:00:00Z",
      });
    }
    if (apiPath === "/monetization/commercial-metrics") {
      return fulfillJson(commercialMetricsPayload);
    }

    return fulfillJson({ detail: `Unhandled screenshot API path: ${apiPath}` });
  });
}

async function stabilizePage(page: import("@playwright/test").Page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        caret-color: transparent !important;
      }
      .flow-ai-assistant,
      img[src="/icon_white.png"] {
        visibility: hidden !important;
      }
    `,
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const fixedNow = new Date("2026-05-22T00:00:00.000Z").getTime();
    const RealDate = Date;
    class FixedDate extends RealDate {
      constructor(...args: ConstructorParameters<DateConstructor>) {
        if (args.length === 0) {
          super(fixedNow);
        } else {
          super(...args);
        }
      }
      static now() {
        return fixedNow;
      }
    }
    window.Date = FixedDate as DateConstructor;
  });
});

test("captures core commercial MVP page baselines", async ({ page }) => {
  await installStableApiRoutes(page);

  const pages = [
    { path: "/dashboard", heading: "Control Dashboard", name: "dashboard" },
    { path: "/orchestrate", heading: "Workflow Orchestrator", name: "orchestrate" },
    { path: "/orchestrations", heading: "Orchestration History", name: "orchestrations" },
    { path: "/monetization", heading: "Plans & Usage", name: "monetization" },
  ] as const;

  for (const item of pages) {
    await page.goto(item.path);
    await stabilizePage(page);
    await expect(page.getByRole("heading", { name: item.heading })).toBeVisible();
    await expect(page.getByText("Request timed out. Please retry.")).toHaveCount(0);
    await expect(page).toHaveScreenshot(`commercial-${item.name}.png`, {
      fullPage: false,
      animations: "disabled",
      mask: [page.getByLabel("Entitlement Token (signed)")],
      maxDiffPixelRatio: 0.03,
    });
  }
});
