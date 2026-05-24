"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";

const workflowSteps = [
  {
    id: "pick",
    label: "Pick gate",
    title: "Start with the AI-generated PR Release Gate",
    body: "Use PR diff summary, CI logs, change risk, and deployment environment as the required evidence package before an agent can affect CI/CD.",
    metric: "PR release gate",
    stage: "Template",
    preview: ["PR diff summary", "CI log evidence", "Deployment environment"],
  },
  {
    id: "run",
    label: "Run with policy",
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
    label: "Audit replay",
    title: "Turn the run into a buyer-readable audit report",
    body: "Each run shows requester, approver, policy gate, queue timeline, step evidence, checkpoint hash, work units, and blocked risk.",
    metric: "audit report",
    stage: "Replay",
    preview: ["Policy gate decision", "Checkpoint hash", "Blocked risk"],
  },
  {
    id: "upgrade",
    label: "Track value",
    title: "Connect governed execution to ROI evidence",
    body: "Billable work units, audited workflow counts, policy blocks, and commercial events make the control layer easy to package.",
    metric: "ROI evidence",
    stage: "Commercial",
    preview: ["Usage counter updated", "Audit event recorded", "Work units captured"],
  },
];

const commercialLadders = [
  { tier: "Free", value: "Try single-step workflows before committing to a paid control loop." },
  { tier: "Pro", value: "Run daily multi-step Planner, Analyzer, and Reviewer workflows." },
  { tier: "Power", value: "Use approval gates, audit evidence, and higher operational limits." },
];

export function TutorialView() {
  const [activeStepId, setActiveStepId] = useState(workflowSteps[0].id);
  const activeStep = useMemo(
    () => workflowSteps.find((step) => step.id === activeStepId) ?? workflowSteps[0],
    [activeStepId]
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
              Run Workflow
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
