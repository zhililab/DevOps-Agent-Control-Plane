"use client";

import { FormEvent, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type { DailyPlanRecord } from "@/lib/types";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function TodayView() {
  const [tasksText, setTasksText] = useState("Fix CI flake\nPrepare deployment notes");
  const [meetingsText, setMeetingsText] = useState("10:30 Platform standup");
  const [blockersText, setBlockersText] = useState("Waiting for infra approval");
  const [prioritiesText, setPrioritiesText] = useState("Fix CI flake");
  const [planRecord, setPlanRecord] = useState<DailyPlanRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  function applyPreset(preset: "release-day" | "incident-day") {
    if (preset === "release-day") {
      setTasksText("Finalize release notes\nRun smoke tests\nPrepare rollback checklist");
      setMeetingsText("10:30 Release sync\n16:00 Stakeholder update");
      setBlockersText("Waiting for final QA signoff");
      setPrioritiesText("Run smoke tests\nFinalize release notes");
      return;
    }

    setTasksText("Stabilize failing pipeline\nReview alert timeline\nDraft incident update");
    setMeetingsText("09:30 Incident triage\n14:00 RCA review");
    setBlockersText("Missing debug logs from worker node");
    setPrioritiesText("Stabilize failing pipeline");
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const result = await apiClient.generateDailyPlan({
        tasks: splitLines(tasksText),
        meetings: splitLines(meetingsText),
        blockers: splitLines(blockersText),
        priorities: splitLines(prioritiesText),
      });
      setPlanRecord(result);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to generate daily plan");
    }
  }

  return (
    <PageCard title="Today" description="Submit daily context and generate an inspectable daily plan.">
      <section className="result-block">
        <h3>Quick Start Templates</h3>
        <p className="muted">Use a scenario preset to speed up planning and keep output consistent.</p>
        <div className="button-row">
          <button type="button" onClick={() => applyPreset("release-day")}>
            Release Day
          </button>
          <button type="button" onClick={() => applyPreset("incident-day")}>
            Incident Response
          </button>
        </div>
      </section>

      <form onSubmit={onSubmit}>
        <label>
          Tasks (one per line)
          <textarea value={tasksText} rows={4} onChange={(event) => setTasksText(event.target.value)} />
        </label>
        <label>
          Meetings (one per line)
          <textarea value={meetingsText} rows={3} onChange={(event) => setMeetingsText(event.target.value)} />
        </label>
        <label>
          Blockers (one per line)
          <textarea value={blockersText} rows={3} onChange={(event) => setBlockersText(event.target.value)} />
        </label>
        <label>
          Priorities (one per line)
          <textarea value={prioritiesText} rows={3} onChange={(event) => setPrioritiesText(event.target.value)} />
        </label>
        <button type="submit">Generate Daily Plan</button>
      </form>

      {error ? <p className="status status-error">{error}</p> : null}

      {planRecord ? (
        <div className="reflection-section">
          <h3>Generated Plan</h3>
          <div className="result-block">
            <p>{planRecord.plan.status_summary}</p>
          </div>

          <div className="result-grid">
            <div className="result-block">
              <h4>Top Priorities</h4>
              <ul>
                {planRecord.plan.top_priorities.map((item) => (
                  <li key={`priority-${item}`}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="result-block">
              <h4>Recommended Order</h4>
              <ol>
                {planRecord.plan.recommended_order.map((item) => (
                  <li key={`order-${item}`}>{item}</li>
                ))}
              </ol>
            </div>

            <div className="result-block">
              <h4>Risks And Reminders</h4>
              <ul>
                {planRecord.plan.risks_and_reminders.map((item) => (
                  <li key={`risk-${item}`}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="result-block">
              <h4>Next Actions</h4>
              <ul>
                {planRecord.plan.next_actions.map((item) => (
                  <li key={`next-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}
    </PageCard>
  );
}
