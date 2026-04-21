"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type { TechnicalAnalysisRecord } from "@/lib/types";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function splitSnippets(value: string): string[] {
  return value
    .split("\n---\n")
    .map((block) => block.trim())
    .filter(Boolean);
}

export function TechnicalAnalysisView() {
  const [issueDescription, setIssueDescription] = useState(
    "Deployment pipeline fails after artifact upload step with intermittent timeout."
  );
  const [errorsText, setErrorsText] = useState(
    "TimeoutError: upstream service did not respond in 30s\nartifact registry upload failed"
  );
  const [logsText, setLogsText] = useState(
    "deploy stage start\nupload artifact to registry\ntimeout while waiting for registry ack\njob failed"
  );
  const [codeSnippetsText, setCodeSnippetsText] = useState("curl --max-time 30 https://registry/api/upload");
  const [latestRecord, setLatestRecord] = useState<TechnicalAnalysisRecord | null>(null);
  const [history, setHistory] = useState<TechnicalAnalysisRecord[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [openSections, setOpenSections] = useState({
    causes: true,
    validation: true,
    fixes: true,
    risks: false,
    followUp: false,
  });

  useEffect(() => {
    async function loadHistory() {
      try {
        const response = await apiClient.listTechnicalAnalyses();
        setHistory(response.items);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load technical analysis history");
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
      const record = await apiClient.generateTechnicalAnalysis({
        issue_description: issueDescription.trim(),
        errors: splitLines(errorsText),
        logs: logsText.trim(),
        code_snippets: splitSnippets(codeSnippetsText),
      });
      setLatestRecord(record);
      setHistory((existing) => [record, ...existing.filter((item) => item.id !== record.id)]);
      setStatus("Technical analysis generated and saved.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to generate technical analysis");
    }
  }

  function applyPreset(preset: "pipeline-timeout" | "permission-denied" | "service-unreachable") {
    if (preset === "pipeline-timeout") {
      setIssueDescription("CI pipeline intermittently times out during artifact upload.");
      setErrorsText("TimeoutError: upstream service did not respond in 30s");
      setLogsText("build done\nupload artifact\ntimeout waiting for registry ack\njob failed");
      setCodeSnippetsText("curl --max-time 30 https://registry/api/upload");
      return;
    }

    if (preset === "permission-denied") {
      setIssueDescription("Deployment job fails when writing image to registry.");
      setErrorsText("permission denied for artifact upload\nforbidden: insufficient_scope");
      setLogsText("deploy start\npush image\nauth check failed\njob failed");
      setCodeSnippetsText("docker push $IMAGE_TAG");
      return;
    }

    setIssueDescription("Service health checks fail due to endpoint not reachable from runtime.");
    setErrorsText("connection refused on target endpoint");
    setLogsText("health check start\nservice unreachable\nretry exhausted");
    setCodeSnippetsText("curl -v http://internal-service:8080/health");
  }

  return (
    <PageCard title="Technical Analysis" description="Analyze DevOps and engineering issues with structured output.">
      <section className="result-block">
        <h3>Quick Start Templates</h3>
        <p className="muted">Pick a common incident pattern to prefill the form and speed up verification.</p>
        <div className="button-row">
          <button type="button" onClick={() => applyPreset("pipeline-timeout")}>
            CI Timeout
          </button>
          <button type="button" onClick={() => applyPreset("permission-denied")}>
            Permission Denied
          </button>
          <button type="button" onClick={() => applyPreset("service-unreachable")}>
            Service Unreachable
          </button>
        </div>
      </section>

      <form onSubmit={onSubmit}>
        <label>
          Issue Description
          <textarea value={issueDescription} rows={4} onChange={(event) => setIssueDescription(event.target.value)} />
        </label>
        <label>
          Errors (one per line)
          <textarea value={errorsText} rows={4} onChange={(event) => setErrorsText(event.target.value)} />
        </label>
        <label>
          Logs
          <textarea value={logsText} rows={5} onChange={(event) => setLogsText(event.target.value)} />
        </label>
        <label>
          Code Snippets (split blocks with line: ---)
          <textarea
            value={codeSnippetsText}
            rows={6}
            onChange={(event) => setCodeSnippetsText(event.target.value)}
          />
        </label>
        <button type="submit">Analyze Technical Issue</button>
      </form>

      {status ? <StatusMessage message={status} tone="success" /> : null}
      {error ? <StatusMessage message={error} tone="error" /> : null}

      {latestRecord ? (
        <section className="reflection-section">
          <h3>Generated Analysis</h3>

          <div className="result-grid">
            <div className="result-block">
              <h4>Problem Statement</h4>
              <p>{latestRecord.output.problem_statement}</p>
            </div>

            <details className="result-block" open={openSections.causes}>
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setOpenSections((current) => ({ ...current, causes: !current.causes }));
                }}
              >
                Likely Causes
              </summary>
              <div>
                <ul>
                  {latestRecord.output.likely_causes.map((item) => (
                    <li key={`cause-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </details>

            <details className="result-block" open={openSections.validation}>
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setOpenSections((current) => ({ ...current, validation: !current.validation }));
                }}
              >
                Validation Steps
              </summary>
              <div>
                <ol>
                  {latestRecord.output.validation_steps.map((item) => (
                    <li key={`validation-${item}`}>{item}</li>
                  ))}
                </ol>
              </div>
            </details>

            <details className="result-block" open={openSections.fixes}>
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setOpenSections((current) => ({ ...current, fixes: !current.fixes }));
                }}
              >
                Fix Options
              </summary>
              <div>
                <ul>
                  {latestRecord.output.fix_options.map((item) => (
                    <li key={`fix-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </details>

            <details className="result-block" open={openSections.risks}>
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setOpenSections((current) => ({ ...current, risks: !current.risks }));
                }}
              >
                Risks
              </summary>
              <div>
                <ul>
                  {latestRecord.output.risks.map((item) => (
                    <li key={`risk-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </details>

            <details className="result-block" open={openSections.followUp}>
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setOpenSections((current) => ({ ...current, followUp: !current.followUp }));
                }}
              >
                Follow-Up Tasks
              </summary>
              <div>
                <ul>
                  {latestRecord.output.follow_up_tasks.map((item) => (
                    <li key={`follow-up-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </details>
          </div>
        </section>
      ) : null}

      <section className="reflection-section">
        <h3>Analysis History</h3>
        {isHistoryLoading ? <p className="muted">Loading analysis history...</p> : null}
        {!isHistoryLoading && history.length === 0 ? <p className="muted">No analyses saved yet.</p> : null}
        {history.map((item) => (
          <article key={item.id} className="history-plan">
            <h4>{item.analysis_date}</h4>
            <p>{item.output.problem_statement}</p>
            <p className="muted">Top fix: {item.output.fix_options[0] ?? "N/A"}</p>
          </article>
        ))}
      </section>
    </PageCard>
  );
}
