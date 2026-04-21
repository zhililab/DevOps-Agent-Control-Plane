"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type { DailyReflectionRecord } from "@/lib/types";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function ReflectionView() {
  const [completedText, setCompletedText] = useState("Closed CI incident");
  const [unfinishedText, setUnfinishedText] = useState("Finalize release checklist");
  const [blockersText, setBlockersText] = useState("Waiting for approval from security");
  const [moodNotesText, setMoodNotesText] = useState("Focused but slightly blocked by dependencies.");
  const [latestRecord, setLatestRecord] = useState<DailyReflectionRecord | null>(null);
  const [history, setHistory] = useState<DailyReflectionRecord[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);

  function applyPreset(preset: "steady-progress" | "blocked-day") {
    if (preset === "steady-progress") {
      setCompletedText("Closed CI incident\nPublished deployment checklist");
      setUnfinishedText("Write short runbook summary");
      setBlockersText("No major blockers");
      setMoodNotesText("Focused and steady. Good execution rhythm.");
      return;
    }

    setCompletedText("Collected error timeline");
    setUnfinishedText("Fix flaky integration test\nPrepare RCA draft");
    setBlockersText("Waiting for owner feedback\nMissing staging credentials");
    setMoodNotesText("Felt blocked by cross-team dependency and delayed access.");
  }

  useEffect(() => {
    async function loadHistory() {
      try {
        const response = await apiClient.listDailyReflections();
        setHistory(response.items);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load reflection history");
      } finally {
        setIsHistoryLoading(false);
      }
    }

    void loadHistory();
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const record = await apiClient.generateDailyReflection({
        completed: splitLines(completedText),
        unfinished: splitLines(unfinishedText),
        blockers: splitLines(blockersText),
        mood_or_notes: moodNotesText.trim(),
      });
      setLatestRecord(record);
      setHistory((existing) => [record, ...existing.filter((item) => item.id !== record.id)]);
      setStatus("Reflection summary generated and saved.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to generate reflection summary");
    }
  }

  return (
    <PageCard title="Reflection" description="Capture end-of-day summary and learning signals.">
      <section className="result-block">
        <h3>Quick Start Templates</h3>
        <p className="muted">Use a reflection preset and adjust details instead of writing from scratch.</p>
        <div className="button-row">
          <button type="button" onClick={() => applyPreset("steady-progress")}>
            Steady Progress
          </button>
          <button type="button" onClick={() => applyPreset("blocked-day")}>
            Blocked Day
          </button>
        </div>
      </section>

      <form onSubmit={onSubmit}>
        <label>
          Completed (one per line)
          <textarea value={completedText} rows={4} onChange={(event) => setCompletedText(event.target.value)} />
        </label>
        <label>
          Unfinished (one per line)
          <textarea value={unfinishedText} rows={4} onChange={(event) => setUnfinishedText(event.target.value)} />
        </label>
        <label>
          Blockers (one per line)
          <textarea value={blockersText} rows={3} onChange={(event) => setBlockersText(event.target.value)} />
        </label>
        <label>
          Mood or notes
          <textarea value={moodNotesText} rows={3} onChange={(event) => setMoodNotesText(event.target.value)} />
        </label>
        <button type="submit">Generate Daily Summary</button>
      </form>

      {status ? <StatusMessage message={status} tone="success" /> : null}
      {error ? <StatusMessage message={error} tone="error" /> : null}

      {latestRecord ? (
        <section className="reflection-section">
          <h3>Generated Daily Summary</h3>
          <div className="result-grid">
            <div className="result-block">
              <p>{latestRecord.summary.day_summary}</p>
            </div>
            <div className="result-block">
              <h4>Unfinished Items</h4>
              <ul>
                {latestRecord.summary.unfinished_items.map((item) => (
                  <li key={`unfinished-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="result-block">
              <h4>Pattern Hints</h4>
              <ul>
                {latestRecord.summary.pattern_hints.map((item) => (
                  <li key={`pattern-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="result-block">
              <h4>Tomorrow Suggestions</h4>
              <ul>
                {latestRecord.summary.tomorrow_suggestions.map((item) => (
                  <li key={`tomorrow-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      <section className="reflection-section">
        <h3>Reflection History</h3>
        {isHistoryLoading ? <p className="muted">Loading reflection history...</p> : null}
        {!isHistoryLoading && history.length === 0 ? <p className="muted">No reflections saved yet.</p> : null}
        {history.map((record) => (
          <article key={record.id} className="history-plan">
            <h4>{record.entry_date}</h4>
            <p>{record.summary.day_summary}</p>
            <p className="muted">Tomorrow: {record.summary.tomorrow_suggestions.join(" | ")}</p>
          </article>
        ))}
      </section>
    </PageCard>
  );
}
