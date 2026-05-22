import Link from "next/link";

import { PageCard } from "@/components/ui/PageCard";

const workflowSteps = [
  {
    title: "1. Pick a DevOps workflow",
    body: "Start with a release gate, incident triage, security hardening, or query performance template.",
  },
  {
    title: "2. Run with entitlement",
    body: "Signed entitlement selects the Free, Pro, or Power boundary before the workflow executes.",
  },
  {
    title: "3. Inspect replay evidence",
    body: "Each step keeps conclusion, evidence, risk, next action, duration, and ledger integrity signals.",
  },
  {
    title: "4. Track commercial value",
    body: "Plans & Usage records subscription state, usage counters, and commercial audit events.",
  },
];

const commercialLadders = [
  { tier: "Free", value: "Try single-step workflows before committing to a paid control loop." },
  { tier: "Pro", value: "Run daily multi-step Planner, Analyzer, and Reviewer workflows." },
  { tier: "Power", value: "Use approval gates, audit evidence, and higher operational limits." },
];

export function TutorialView() {
  return (
    <PageCard
      title="Tutorial"
      description="A short commercial onboarding path for trusted DevOps agent orchestration."
    >
      <section className="tutorial-hero" aria-label="tutorial-overview">
        <div>
          <p className="eyebrow">FROM DEMO TO PAID WORKFLOW</p>
          <h3>Show the value path: run, replay, verify, then upgrade.</h3>
          <p className="muted">
            The MVP is strongest when a user can see one operational workflow become auditable evidence and a billable
            work unit.
          </p>
        </div>
        <div className="tutorial-motion" aria-hidden="true">
          <span>run</span>
          <span>replay</span>
          <span>verify</span>
          <span>upgrade</span>
        </div>
      </section>

      <section className="tutorial-grid" aria-label="workflow-tutorial">
        {workflowSteps.map((step) => (
          <article className="tutorial-card" key={step.title}>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
          </article>
        ))}
      </section>

      <section className="tutorial-grid tutorial-grid-three" aria-label="commercial-plan-guide">
        {commercialLadders.map((item) => (
          <article className="tutorial-card" key={item.tier}>
            <p className="eyebrow">{item.tier}</p>
            <p>{item.value}</p>
          </article>
        ))}
      </section>

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
    </PageCard>
  );
}
