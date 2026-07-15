"use client";

import { useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type {
  DecisionFeedbackSummary,
  EvaluationCaseList,
  EvaluationRun,
  LlmInvocation,
  LlmProviderStatus,
  PilotComparison,
  PilotMeasurementMetric,
  ReleaseGateDecision,
} from "@/lib/types";


const EMPTY_FEEDBACK: DecisionFeedbackSummary = {
  total: 0,
  accepted: 0,
  rejected: 0,
  corrected: 0,
  acceptance_rate: 0,
  correction_rate: 0,
  reviewed_accuracy: 0,
  false_positive_rate: 0,
  false_negative_rate: 0,
  recent: [],
};

const EMPTY_COMPARISON: PilotComparison = {
  subject: "demo-user",
  team_subject: "demo-team",
  source: "not_configured",
  metrics: [],
  measured_value_summary: "Record baseline and pilot observations to create measured ROI evidence.",
  estimated_roi_remains_separate: true,
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function metricLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function QualityLabView() {
  const [provider, setProvider] = useState<LlmProviderStatus | null>(null);
  const [cases, setCases] = useState<EvaluationCaseList | null>(null);
  const [latestRun, setLatestRun] = useState<EvaluationRun | null>(null);
  const [feedback, setFeedback] = useState<DecisionFeedbackSummary>(EMPTY_FEEDBACK);
  const [invocations, setInvocations] = useState<LlmInvocation[]>([]);
  const [comparison, setComparison] = useState<PilotComparison>(EMPTY_COMPARISON);
  const [status, setStatus] = useState("Loading quality evidence...");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [actor, setActor] = useState("interview-reviewer");
  const [corrections, setCorrections] = useState<Record<number, ReleaseGateDecision>>({});
  const [subject, setSubject] = useState("demo-user");
  const [teamSubject, setTeamSubject] = useState("demo-team");
  const [metric, setMetric] = useState<PilotMeasurementMetric>("review_minutes");
  const [phase, setPhase] = useState<"baseline" | "pilot">("baseline");
  const [measurementValue, setMeasurementValue] = useState("30");
  const [sampleSize, setSampleSize] = useState("1");
  const [writeAccess, setWriteAccess] = useState("");

  async function loadQualityEvidence() {
    const results = await Promise.allSettled([
      apiClient.getLlmProviderStatus(),
      apiClient.listEvaluationCases(),
      apiClient.getLatestEvaluationRun(),
      apiClient.getDecisionFeedbackSummary(),
      apiClient.listLlmInvocations(12),
      apiClient.getPilotComparison(subject, teamSubject),
    ]);
    const failures: string[] = [];
    if (results[0].status === "fulfilled") setProvider(results[0].value);
    else failures.push("provider status");
    if (results[1].status === "fulfilled") setCases(results[1].value);
    else failures.push("evaluation cases");
    if (results[2].status === "fulfilled") setLatestRun(results[2].value);
    else failures.push("latest evaluation");
    if (results[3].status === "fulfilled") setFeedback(results[3].value);
    else failures.push("feedback summary");
    if (results[4].status === "fulfilled") setInvocations(results[4].value.items);
    else failures.push("model invocations");
    if (results[5].status === "fulfilled") setComparison(results[5].value);
    else failures.push("pilot comparison");
    setStatus(failures.length ? `Some quality evidence is unavailable: ${failures.join(", ")}.` : "Quality evidence loaded.");
  }

  useEffect(() => {
    void loadQualityEvidence();
    // Initial account defaults intentionally load once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const caseNameById = useMemo(
    () => new Map((cases?.items ?? []).map((item) => [item.id, item.name])),
    [cases]
  );

  async function runEvaluation(mode: "deterministic" | "live") {
    setBusy(true);
    setError("");
    setStatus(`Running ${mode} evaluation across ${cases?.items.length ?? 25} fixed cases...`);
    try {
      const result = await apiClient.runEvaluation(mode, [], writeAccess);
      setLatestRun(result);
      const invocationResponse = await apiClient.listLlmInvocations(12);
      setInvocations(invocationResponse.items);
      setStatus(`${mode === "live" ? "Live model" : "Deterministic"} evaluation completed.`);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Evaluation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitFeedback(
    resultId: number,
    verdict: "accepted" | "rejected" | "corrected"
  ) {
    setBusy(true);
    setError("");
    try {
      await apiClient.createDecisionFeedback({
        evaluation_case_result_id: resultId,
        verdict,
        corrected_decision: verdict === "corrected" ? corrections[resultId] ?? "needs human review" : undefined,
        actor,
      }, writeAccess);
      setFeedback(await apiClient.getDecisionFeedbackSummary());
      setStatus("Human decision feedback recorded as an append-only review event.");
    } catch (feedbackError) {
      setError(feedbackError instanceof Error ? feedbackError.message : "Feedback failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveMeasurement() {
    const value = Number(measurementValue);
    const samples = Number(sampleSize);
    if (!Number.isFinite(value) || value < 0 || !Number.isInteger(samples) || samples < 1) {
      setError("Measurement value and sample size must be valid non-negative numbers.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiClient.createPilotMeasurement({
        subject,
        team_subject: teamSubject,
        metric,
        phase,
        value,
        unit: metric === "incidents" ? "count" : "minutes",
        sample_size: samples,
        source: "observed",
      }, writeAccess);
      setComparison(await apiClient.getPilotComparison(subject, teamSubject));
      setStatus(`${phase} measurement saved; estimated ROI remains separately labeled.`);
    } catch (measurementError) {
      setError(measurementError instanceof Error ? measurementError.message : "Measurement failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageCard
      title="Agent Quality Lab"
      description="Model observability, fixed PR/CI evaluation, human feedback, and measured pilot evidence."
    >
      <section className="quality-hero" aria-label="quality-operating-model">
        <div>
          <p className="eyebrow">INTERVIEW EVIDENCE</p>
          <h3>Prove the Agent decision, not just the workflow.</h3>
          <p className="muted">
            Deterministic policy remains authoritative. The model recommendation is measured, versioned, and reviewable.
          </p>
        </div>
        <div className={`quality-provider ${provider?.configured ? "quality-provider-ready" : ""}`}>
          <span>Provider</span>
          <strong>{provider?.provider ?? "loading"}</strong>
          <small>{provider?.configured ? `${provider.model} · ${provider.prompt_version}` : "Configuration required"}</small>
        </div>
      </section>

      <StatusMessage message={error || status} tone={error ? "error" : "default"} />

      {provider?.write_protected ? (
        <section className="reflection-section" aria-label="quality-write-access">
          <p className="eyebrow">PROTECTED ACTIONS</p>
          <h3>Quality Write Access</h3>
          <p className="muted">Required only to run evaluations or record review evidence. The value stays in memory for this page.</p>
          <label className="quality-actor">
            Access key
            <input
              type="password"
              autoComplete="off"
              value={writeAccess}
              onChange={(event) => setWriteAccess(event.target.value)}
            />
          </label>
        </section>
      ) : null}

      <section className="reflection-section" aria-label="fixed-evaluation">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">FIXED DATASET</p>
            <h3>PR/CI Decision Evaluation</h3>
            <p className="muted">{cases?.dataset_version ?? "pr-ci-gate.v1"} · {cases?.items.length ?? 25} versioned cases</p>
          </div>
          <div className="button-row">
            <button disabled={busy || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void runEvaluation("deterministic")}>Run Rules Baseline</button>
            <button disabled={busy || !provider?.configured || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void runEvaluation("live")}>Run Live Model</button>
          </div>
        </div>

        <div className="kpi-grid quality-kpi-grid">
          <article className="kpi-card"><p className="kpi-label">Accuracy</p><p className="kpi-value">{percent(latestRun?.accuracy ?? 0)}</p><p className="muted">{latestRun?.correct_count ?? 0}/{latestRun?.case_count ?? 0} exact decisions</p></article>
          <article className="kpi-card"><p className="kpi-label">False Positive</p><p className="kpi-value">{latestRun?.false_positive_count ?? 0}</p><p className="muted">Safe change escalated</p></article>
          <article className="kpi-card"><p className="kpi-label">False Negative</p><p className="kpi-value">{latestRun?.false_negative_count ?? 0}</p><p className="muted">Risky change approved</p></article>
          <article className="kpi-card"><p className="kpi-label">Model Cost</p><p className="kpi-value">${(latestRun?.estimated_cost_usd ?? 0).toFixed(4)}</p><p className="muted">{latestRun?.input_tokens ?? 0} in · {latestRun?.output_tokens ?? 0} out · {latestRun?.average_latency_ms ?? 0}ms avg</p></article>
        </div>

        {latestRun?.results.length ? (
          <div className="quality-result-list">
            {latestRun.results.map((result) => (
              <article className="quality-result-row" key={result.id}>
                <div>
                  <strong>{caseNameById.get(result.case_id) ?? result.case_id}</strong>
                  <p className="muted">expected {result.expected_decision} · agent {result.actual_decision} · confidence {percent(result.confidence)}</p>
                </div>
                <span className={result.is_correct ? "quality-pass" : "quality-fail"}>{result.is_correct ? "match" : "mismatch"}</span>
                <div className="quality-feedback-actions">
                  <button disabled={busy || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void submitFeedback(result.id, "accepted")}>Accept</button>
                  <button disabled={busy || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void submitFeedback(result.id, "rejected")}>Reject</button>
                  <select
                    aria-label={`Correct decision for ${result.case_id}`}
                    value={corrections[result.id] ?? "needs human review"}
                    onChange={(event) => setCorrections((current) => ({ ...current, [result.id]: event.target.value as ReleaseGateDecision }))}
                  >
                    <option value="approve">approve</option>
                    <option value="needs human review">needs human review</option>
                    <option value="block">block</option>
                  </select>
                  <button disabled={busy || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void submitFeedback(result.id, "corrected")}>Correct</button>
                </div>
              </article>
            ))}
          </div>
        ) : <p className="muted">Run the fixed dataset to create reproducible quality evidence.</p>}
      </section>

      <section className="reflection-section" aria-label="human-feedback">
        <div className="section-heading-row">
          <div><p className="eyebrow">HUMAN FEEDBACK</p><h3>Decision Review Loop</h3></div>
          <label className="quality-actor">Reviewer<input value={actor} onChange={(event) => setActor(event.target.value)} /></label>
        </div>
        <div className="kpi-grid quality-kpi-grid">
          <article className="kpi-card"><p className="kpi-label">Reviewed</p><p className="kpi-value">{feedback.total}</p><p className="muted">append-only feedback events</p></article>
          <article className="kpi-card"><p className="kpi-label">Acceptance Rate</p><p className="kpi-value">{percent(feedback.acceptance_rate)}</p><p className="muted">{feedback.accepted} accepted</p></article>
          <article className="kpi-card"><p className="kpi-label">Reviewed Accuracy</p><p className="kpi-value">{percent(feedback.reviewed_accuracy)}</p><p className="muted">after explicit corrections</p></article>
          <article className="kpi-card"><p className="kpi-label">Correction Rate</p><p className="kpi-value">{percent(feedback.correction_rate)}</p><p className="muted">{feedback.corrected} corrected</p></article>
        </div>
      </section>

      <section className="reflection-section" aria-label="pilot-measurement">
        <p className="eyebrow">MEASURED ROI</p>
        <h3>Baseline vs Pilot</h3>
        <p className="muted">Observed values stay separate from directional ROI assumptions.</p>
        <div className="quality-measurement-form">
          <label>Account<input value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
          <label>Team<input value={teamSubject} onChange={(event) => setTeamSubject(event.target.value)} /></label>
          <label>Metric<select value={metric} onChange={(event) => setMetric(event.target.value as PilotMeasurementMetric)}><option value="review_minutes">Review minutes</option><option value="audit_minutes">Audit minutes</option><option value="release_lead_time_minutes">Release lead time</option><option value="incidents">Incidents</option><option value="rollback_minutes">Rollback minutes</option></select></label>
          <label>Phase<select value={phase} onChange={(event) => setPhase(event.target.value as "baseline" | "pilot")}><option value="baseline">Baseline</option><option value="pilot">Pilot</option></select></label>
          <label>Observed value<input type="number" min="0" value={measurementValue} onChange={(event) => setMeasurementValue(event.target.value)} /></label>
          <label>Sample size<input type="number" min="1" value={sampleSize} onChange={(event) => setSampleSize(event.target.value)} /></label>
          <button disabled={busy || Boolean(provider?.write_protected && !writeAccess.trim())} onClick={() => void saveMeasurement()}>Save Observation</button>
        </div>
        <div className="quality-comparison-grid">
          {comparison.metrics.length ? comparison.metrics.map((item) => (
            <article className="kpi-card" key={item.metric}>
              <p className="kpi-label">{metricLabel(item.metric)}</p>
              <p className="kpi-value">{item.baseline_value ?? "-"} → {item.pilot_value ?? "-"}</p>
              <p className="muted">{item.improvement_rate === null ? "Need both phases" : `${percent(item.improvement_rate)} improvement`} · {item.unit}</p>
            </article>
          )) : <p className="muted">{comparison.measured_value_summary}</p>}
        </div>
      </section>

      <section className="reflection-section" aria-label="model-observability">
        <p className="eyebrow">MODEL OBSERVABILITY</p>
        <h3>Recent Provider Calls</h3>
        <div className="event-feed">
          {invocations.length ? invocations.map((item) => (
            <article className="event-row" key={item.id}>
              <div><strong>{item.model}</strong><p className="muted">{item.prompt_version} · {item.decision} · {item.input_tokens + item.output_tokens} tokens</p></div>
              <span>{item.latency_ms}ms · ${item.estimated_cost_usd.toFixed(4)}</span>
            </article>
          )) : <p className="muted">No model calls recorded. Keys are never persisted.</p>}
        </div>
      </section>
    </PageCard>
  );
}
