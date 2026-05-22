"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";

const workflowSteps = [
  {
    id: "pick",
    label: "Pick workflow",
    title: "Start from a proven DevOps control loop",
    body: "Choose a release gate, incident triage, security hardening, or query performance template instead of writing a blank prompt.",
    metric: "12 curated templates",
    stage: "Template",
    preview: ["Release gate readiness", "Incident triage replay", "Query performance audit"],
  },
  {
    id: "run",
    label: "Run with policy",
    title: "Execute only after the tier and policy boundary are clear",
    body: "Signed entitlement selects Free, Pro, or Power before the workflow starts, so high-risk runs can require approval first.",
    metric: "free/pro/power gate",
    stage: "Policy",
    preview: ["Signed entitlement verified", "Power approval required", "No legacy tier header"],
  },
  {
    id: "replay",
    label: "Inspect replay",
    title: "Turn the run into evidence someone can inspect",
    body: "Each step preserves conclusion, evidence, risk, next action, duration, and ledger integrity signals for later review.",
    metric: "ledger integrity visible",
    stage: "Replay",
    preview: ["Planner conclusion", "Analyzer evidence", "Reviewer next action"],
  },
  {
    id: "upgrade",
    label: "Track value",
    title: "Connect trusted execution to a billable work unit",
    body: "Plans & Usage records subscription state, usage counters, and commercial audit events without adding payment complexity yet.",
    metric: "manual billing ready",
    stage: "Commercial",
    preview: ["Usage counter updated", "Audit event recorded", "Upgrade path clear"],
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
      description="A short commercial onboarding path for trusted DevOps agent orchestration."
    >
      <section className="tutorial-showcase" aria-label="tutorial-overview">
        <div className="tutorial-showcase-copy">
          <p className="eyebrow">FROM DEMO TO PAID WORKFLOW</p>
          <h3>Run the workflow, inspect the evidence, then show the upgrade path.</h3>
          <p className="muted">
            The MVP is strongest when one operational task visibly becomes trusted replay evidence and a measurable
            commercial work unit.
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
