"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type { PilotScenario, PilotScenarioCompletion, PilotScenarioCompletionSummary } from "@/lib/types";

const workflowSteps = [
  {
    id: "pick",
    label: "Import PR context",
    title: "Start from a controlled PR and CI evidence packet",
    body: "Use PR URL, diff summary, CI log summary, target environment, and change risk as the auditable packet before an agent can affect CI/CD.",
    metric: "PR/CI adapter",
    stage: "Adapter",
    preview: ["PR URL", "CI log summary", "Deployment environment"],
  },
  {
    id: "run",
    label: "Run gate",
    title: "Let policy decide whether the agent can proceed",
    body: "Signed entitlement, required tier, risk level, allowed tool scope, and approval requirement are checked before execution.",
    metric: "power approval gate",
    stage: "Policy",
    preview: ["Signed entitlement verified", "CI/CD scope limited", "No plain tier header"],
  },
  {
    id: "approve",
    label: "Capture team approval",
    title: "Record who requested and who approved the gate",
    body: "Requester, approver, team, and approval note travel with the run so release responsibility is inspectable after the fact.",
    metric: "human approval",
    stage: "Trust",
    preview: ["Team platform-team", "Requested by SRE lead", "Approved by release manager"],
  },
  {
    id: "checkpoint",
    label: "Checkpoint state",
    title: "Persist explicit state snapshots for recovery",
    body: "Accepted, step-started, step-finished, queue retry, cancel, and completion checkpoints make the workflow inspectable after refresh or redeploy.",
    metric: "state snapshots",
    stage: "Checkpoint",
    preview: ["orchestration.accepted", "step.success", "queue.succeeded"],
  },
  {
    id: "replay",
    label: "Verify evidence",
    title: "Turn the run into a buyer-readable audit report",
    body: "Each run shows requester, approver, policy gate, queue timeline, step evidence, checkpoint hash, work units, and blocked risk.",
    metric: "audit report",
    stage: "Replay",
    preview: ["Policy gate decision", "Checkpoint hash", "Blocked risk"],
  },
  {
    id: "upgrade",
    label: "See ROI",
    title: "Connect governed execution to ROI evidence",
    body: "Billable work units, audited workflow counts, policy blocks, and commercial events make the control layer easy to package.",
    metric: "ROI evidence",
    stage: "Commercial",
    preview: ["Usage counter updated", "Audit event recorded", "Work units captured"],
  },
];

const fallbackPilotDatasets: Array<Pick<PilotScenario, "id" | "name" | "success_signal" | "required_tier" | "expected_gate_behavior">> = [
  {
    id: "high-risk-generated-pr",
    name: "High-risk generated PR",
    success_signal: "Power-gated release evidence with human approval and ROI.",
    required_tier: "power",
    expected_gate_behavior: "needs human review",
  },
  {
    id: "low-risk-docs-pr",
    name: "Low-risk docs PR",
    success_signal: "Approved low-risk path with exportable evidence.",
    required_tier: "power",
    expected_gate_behavior: "approve",
  },
  {
    id: "ci-flaky-release",
    name: "CI flaky release",
    success_signal: "Needs-review path with checkpointed retry evidence.",
    required_tier: "power",
    expected_gate_behavior: "needs human review",
  },
  {
    id: "missing-approval",
    name: "Missing approval",
    success_signal: "Initial run returns 409 until approval is confirmed.",
    required_tier: "power",
    expected_gate_behavior: "block",
  },
  {
    id: "rollback-sensitive-release",
    name: "Rollback-sensitive release",
    success_signal: "Blocked risk value captured before release.",
    required_tier: "power",
    expected_gate_behavior: "block",
  },
];

const commercialLadders = [
  { tier: "Free", value: "Try single-step workflows before committing to a paid control loop." },
  { tier: "Pro", value: "Run daily multi-step Planner, Analyzer, and Reviewer workflows." },
  { tier: "Power", value: "Use approval gates, audit evidence, and higher operational limits." },
];

const fallbackScenarioCompletion: PilotScenarioCompletionSummary = {
  total: 5,
  completed: 0,
  needs_evidence: 0,
  missing: 5,
  next_scenario_id: "high-risk-generated-pr",
  ready_for_buyer_review: false,
};

export function TutorialView() {
  const [activeStepId, setActiveStepId] = useState(workflowSteps[0].id);
  const [pilotDatasets, setPilotDatasets] = useState(fallbackPilotDatasets);
  const [scenarioStatuses, setScenarioStatuses] = useState<PilotScenarioCompletion[]>([]);
  const [scenarioCompletion, setScenarioCompletion] = useState<PilotScenarioCompletionSummary>(fallbackScenarioCompletion);
  const activeStep = useMemo(
    () => workflowSteps.find((step) => step.id === activeStepId) ?? workflowSteps[0],
    [activeStepId]
  );

  useEffect(() => {
    let mounted = true;
    async function loadScenarios() {
      try {
        const [scenarioResult, reportResult] = await Promise.allSettled([
          apiClient.listPilotScenarios(),
          apiClient.getPilotReadinessReport(7, "demo-user"),
        ]);
        if (
          mounted &&
          scenarioResult.status === "fulfilled" &&
          Array.isArray(scenarioResult.value.items) &&
          scenarioResult.value.items.length > 0
        ) {
          setPilotDatasets(scenarioResult.value.items);
        }
        if (
          mounted &&
          reportResult.status === "fulfilled" &&
          Array.isArray(reportResult.value.scenario_statuses)
        ) {
          setScenarioStatuses(reportResult.value.scenario_statuses);
          setScenarioCompletion(reportResult.value.scenario_completion ?? fallbackScenarioCompletion);
        }
      } catch {
        if (mounted) {
          setPilotDatasets(fallbackPilotDatasets);
        }
      }
    }
    void loadScenarios();
    return () => {
      mounted = false;
    };
  }, []);

  const scenarioStatusById = useMemo(
    () => new Map(scenarioStatuses.map((item) => [item.id, item])),
    [scenarioStatuses]
  );
  const nextScenario = useMemo(
    () => pilotDatasets.find((item) => item.id === scenarioCompletion.next_scenario_id),
    [pilotDatasets, scenarioCompletion.next_scenario_id]
  );

  return (
    <PageCard
      title="Tutorial"
      description="A buyer story for letting agents into CI/CD and incident response without losing control."
    >
      <section className="tutorial-showcase" aria-label="tutorial-overview">
        <div className="tutorial-showcase-copy">
          <p className="eyebrow">BUYER STORY</p>
          <h3>Let enterprises connect agents to CI/CD and incident response without losing control.</h3>
          <p className="muted">
            The commercial demo is one closed loop: Coding Agent generates a PR, the control plane gates the release,
            a human approves, execution is allowed or blocked, and the audit ledger proves what happened.
          </p>
          <div className="tutorial-actions">
            <Link className="nav-link nav-link-active" href="/orchestrate">
              Run Pilot Gate
            </Link>
            <Link className="nav-link" href="/orchestrations">
              Inspect Replay
            </Link>
            <Link className="nav-link" href="/monetization">
              Compare Plans
            </Link>
          </div>
        </div>
        <div className="tutorial-stage" aria-live="polite">
          <div className="tutorial-stage-header">
            <span>{activeStep.stage}</span>
            <strong>{activeStep.metric}</strong>
          </div>
          <h3>{activeStep.title}</h3>
          <p>{activeStep.body}</p>
          <div className="tutorial-preview-stack">
            {activeStep.preview.map((line) => (
              <span key={line}>{line}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="tutorial-stepper" aria-label="workflow-tutorial">
        {workflowSteps.map((step, index) => (
          <button
            aria-pressed={activeStep.id === step.id}
            className={`tutorial-step-button ${activeStep.id === step.id ? "tutorial-step-active" : ""}`}
            key={step.id}
            onClick={() => setActiveStepId(step.id)}
            type="button"
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{step.label}</strong>
            <p>{step.body}</p>
          </button>
        ))}
      </section>

      <section className="result-block" aria-label="pilot-progress">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Pilot Control Console</p>
            <h3>
              {scenarioCompletion.completed}/{scenarioCompletion.total} scenario gates completed
            </h3>
            <p className="muted">
              Buyer review status: {scenarioCompletion.ready_for_buyer_review ? "Ready" : "Not ready"}
              {nextScenario ? ` · next scenario: ${nextScenario.name}` : ""}
            </p>
          </div>
          {nextScenario ? (
            <Link className="nav-link nav-link-active" href={`/orchestrate?scenario=${nextScenario.id}`}>
              Run Next Scenario
            </Link>
          ) : (
            <Link className="nav-link nav-link-active" href="/monetization">
              Review Closeout
            </Link>
          )}
        </div>
        <p className="muted">
          Run each scenario one at a time, verify ledger/checkpoint evidence, then use Plans & Usage for the closeout report.
        </p>
      </section>

      <section className="tutorial-grid tutorial-grid-three" aria-label="pilot-demo-datasets">
        {pilotDatasets.map((item) => {
          const status = scenarioStatusById.get(item.id)?.status ?? "missing";
          return (
            <article className="tutorial-card" key={item.id}>
              <p className="eyebrow">Pilot Dataset · {status}</p>
              <h3>{item.name}</h3>
              <p>{item.success_signal}</p>
              <p className="muted">
                {item.required_tier.toUpperCase()} · {item.expected_gate_behavior}
                {item.id === "missing-approval" ? " · first run should block until approval is confirmed" : ""}
              </p>
              <Link className="nav-link nav-link-active" href={`/orchestrate?scenario=${item.id}`}>
                Run Scenario
              </Link>
            </article>
          );
        })}
      </section>

      <section className="tutorial-grid tutorial-grid-three tutorial-plan-guide" aria-label="commercial-plan-guide">
        {commercialLadders.map((item) => (
          <article className="tutorial-card" key={item.tier}>
            <p className="eyebrow">{item.tier}</p>
            <p>{item.value}</p>
          </article>
        ))}
      </section>
    </PageCard>
  );
}
