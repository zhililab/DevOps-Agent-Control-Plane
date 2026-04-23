"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeGraphPreview } from "@/components/charts/KnowledgeGraphPreview";
import { MiniBarTrend } from "@/components/charts/MiniBarTrend";
import { MiniLineTrend } from "@/components/charts/MiniLineTrend";
import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type {
  DailyPlanRecord,
  DailyReflectionRecord,
  TechnicalAnalysisRecord,
  WorkflowOrchestrationRecord,
  WorkflowOrchestrationMetrics,
} from "@/lib/types";

type DashboardState = {
  plans: DailyPlanRecord[];
  reflections: DailyReflectionRecord[];
  analyses: TechnicalAnalysisRecord[];
  orchestrations: WorkflowOrchestrationRecord[];
  orchestrationMetrics: WorkflowOrchestrationMetrics;
};

const DEFAULT_ORCHESTRATION_METRICS: WorkflowOrchestrationMetrics = {
  period_days: 7,
  total_runs: 0,
  weekly_active_orchestrations: 0,
  partial_success_rate: 0,
  average_duration_ms: 0,
};

const DASHBOARD_WINDOW_OPTIONS = [7, 30] as const;

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDurationMs(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }
  return `${Math.round(value)}ms`;
}

function buildRecentDateKeys(days: number): string[] {
  return buildDateKeysForWindow(days, 0);
}

function buildDateKeysForWindow(days: number, offsetDays: number): string[] {
  const result: string[] = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i -= 1) {
    const current = new Date(now);
    current.setDate(now.getDate() - offsetDays - i);
    result.push(current.toISOString().slice(0, 10));
  }
  return result;
}

function toTrendData(keys: string[], records: string[]) {
  const countByDate = new Map<string, number>();
  records.forEach((record) => {
    countByDate.set(record, (countByDate.get(record) ?? 0) + 1);
  });

  return keys.map((key) => ({
    label: key.slice(5),
    value: countByDate.get(key) ?? 0,
  }));
}

function hasItemsPayload(value: unknown): value is { items: unknown[] } {
  if (!value || typeof value !== "object") return false;
  const items = (value as { items?: unknown }).items;
  return Array.isArray(items);
}

function hasOrchestrationMetricsPayload(value: unknown): value is WorkflowOrchestrationMetrics {
  if (!value || typeof value !== "object") return false;
  const metrics = value as Partial<WorkflowOrchestrationMetrics>;
  return (
    typeof metrics.period_days === "number" &&
    typeof metrics.total_runs === "number" &&
    typeof metrics.weekly_active_orchestrations === "number" &&
    typeof metrics.partial_success_rate === "number" &&
    typeof metrics.average_duration_ms === "number"
  );
}

type OrchestrationWindowStats = {
  runs: number;
  partialSuccessCount: number;
  failedCount: number;
};

type OrchestrationPeriodStats = {
  current: OrchestrationWindowStats;
  previous: OrchestrationWindowStats;
};

function emptyWindowStats(): OrchestrationWindowStats {
  return { runs: 0, partialSuccessCount: 0, failedCount: 0 };
}

function buildOrchestrationPeriodStats(
  orchestrations: WorkflowOrchestrationRecord[],
  windowDays: number
): OrchestrationPeriodStats {
  const currentSet = new Set(buildDateKeysForWindow(windowDays, 0));
  const previousSet = new Set(buildDateKeysForWindow(windowDays, windowDays));
  const current = emptyWindowStats();
  const previous = emptyWindowStats();

  orchestrations.forEach((item) => {
    const dateKey = item.created_at?.slice(0, 10);
    if (!dateKey) return;
    const isCurrent = currentSet.has(dateKey);
    const isPrevious = previousSet.has(dateKey);
    if (!isCurrent && !isPrevious) return;

    const target = isCurrent ? current : previous;
    target.runs += 1;
    if (item.status === "partial_success") {
      target.partialSuccessCount += 1;
    }
    if (item.status === "failed") {
      target.failedCount += 1;
    }
  });

  return { current, previous };
}

function toPartialSuccessRate(stats: OrchestrationWindowStats): number {
  return stats.runs > 0 ? stats.partialSuccessCount / stats.runs : 0;
}

function toPartialFailRatio(stats: OrchestrationWindowStats): number {
  return (stats.partialSuccessCount + 1) / (stats.failedCount + 1);
}

function formatSignedInteger(value: number): string {
  if (value > 0) return `+${value}`;
  return `${value}`;
}

function formatSignedPercentPoint(value: number): string {
  const inPoints = value * 100;
  const rounded = Math.abs(inPoints) < 0.05 ? 0 : inPoints;
  const formatted = rounded.toFixed(1);
  if (rounded > 0) return `+${formatted}pp`;
  return `${formatted}pp`;
}

function deltaClassName(value: number, inverse = false): string {
  if (Math.abs(value) < 0.0001) return "kpi-delta-neutral";
  const isPositive = value > 0;
  if (inverse) {
    return isPositive ? "kpi-delta-negative" : "kpi-delta-positive";
  }
  return isPositive ? "kpi-delta-positive" : "kpi-delta-negative";
}

function buildAnomalyHints(stats: OrchestrationPeriodStats, windowDays: number): string[] {
  const hints: string[] = [];
  const currentRuns = stats.current.runs;
  const previousRuns = stats.previous.runs;

  if (previousRuns >= 6 && currentRuns <= previousRuns * 0.5) {
    hints.push(`Sharp run drop: ${currentRuns} runs vs ${previousRuns} in the previous ${windowDays}-day window.`);
  }

  const currentRatio = toPartialFailRatio(stats.current);
  const previousRatio = toPartialFailRatio(stats.previous);
  if (
    stats.current.runs >= 4 &&
    stats.previous.runs >= 4 &&
    currentRatio >= previousRatio * 1.75 &&
    stats.current.partialSuccessCount >= 2
  ) {
    hints.push(
      `Partial-success/fail ratio spiked from ${previousRatio.toFixed(2)} to ${currentRatio.toFixed(2)}.`
    );
  }

  return hints;
}

export function DashboardView() {
  const [state, setState] = useState<DashboardState>({
    plans: [],
    reflections: [],
    analyses: [],
    orchestrations: [],
    orchestrationMetrics: DEFAULT_ORCHESTRATION_METRICS,
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [orchestrationWindowDays, setOrchestrationWindowDays] = useState<7 | 30>(7);
  const [orchestrationLoading, setOrchestrationLoading] = useState(false);
  const [orchestrationError, setOrchestrationError] = useState<string | null>(null);
  const storyRefs = useRef<Array<HTMLElement | null>>([]);

  useEffect(() => {
    async function load() {
      const [plansResult, reflectionsResult, analysesResult] = await Promise.allSettled([
        apiClient.listDailyPlans(),
        apiClient.listDailyReflections(),
        apiClient.listTechnicalAnalyses(),
      ]);

      const plans =
        plansResult.status === "fulfilled" && hasItemsPayload(plansResult.value) ? plansResult.value.items : [];
      const reflections =
        reflectionsResult.status === "fulfilled" && hasItemsPayload(reflectionsResult.value)
          ? reflectionsResult.value.items
          : [];
      const analyses =
        analysesResult.status === "fulfilled" && hasItemsPayload(analysesResult.value)
          ? analysesResult.value.items
          : [];
      const nextState: DashboardState = {
        plans,
        reflections,
        analyses,
        orchestrations: [],
        orchestrationMetrics: { ...DEFAULT_ORCHESTRATION_METRICS },
      };
      setState(nextState);

      const failedEndpoints: string[] = [];
      if (plansResult.status === "rejected" || (plansResult.status === "fulfilled" && !hasItemsPayload(plansResult.value))) {
        failedEndpoints.push("plans");
      }
      if (
        reflectionsResult.status === "rejected" ||
        (reflectionsResult.status === "fulfilled" && !hasItemsPayload(reflectionsResult.value))
      ) {
        failedEndpoints.push("reflections");
      }
      if (
        analysesResult.status === "rejected" ||
        (analysesResult.status === "fulfilled" && !hasItemsPayload(analysesResult.value))
      ) {
        failedEndpoints.push("analysis");
      }
      if (failedEndpoints.length > 0) {
        setError(`Some dashboard data is unavailable: ${failedEndpoints.join(", ")}.`);
      } else {
        setError(null);
      }
      setIsLoading(false);
    }

    void load();
  }, []);

  useEffect(() => {
    async function loadOrchestrationWindow() {
      setOrchestrationLoading(true);

      const [metricsResult, historyResult] = await Promise.allSettled([
        apiClient.getWorkflowOrchestrationMetrics(orchestrationWindowDays),
        apiClient.listWorkflowOrchestrations({ limit: 200 }),
      ]);

      const metrics =
        metricsResult.status === "fulfilled" && hasOrchestrationMetricsPayload(metricsResult.value)
          ? metricsResult.value
          : { ...DEFAULT_ORCHESTRATION_METRICS, period_days: orchestrationWindowDays };
      const orchestrations =
        historyResult.status === "fulfilled" && hasItemsPayload(historyResult.value) ? historyResult.value.items : [];

      setState((prev) => ({
        ...prev,
        orchestrationMetrics: metrics,
        orchestrations,
      }));

      const failedEndpoints: string[] = [];
      if (metricsResult.status === "rejected" || (metricsResult.status === "fulfilled" && !hasOrchestrationMetricsPayload(metricsResult.value))) {
        failedEndpoints.push("orchestration metrics");
      }
      if (historyResult.status === "rejected" || (historyResult.status === "fulfilled" && !hasItemsPayload(historyResult.value))) {
        failedEndpoints.push("orchestration history");
      }

      if (failedEndpoints.length > 0) {
        setOrchestrationError(`Some dashboard data is unavailable: ${failedEndpoints.join(", ")}.`);
      } else {
        setOrchestrationError(null);
      }
      setOrchestrationLoading(false);
    }

    void loadOrchestrationWindow();
  }, [orchestrationWindowDays]);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      storyRefs.current.forEach((node) => {
        if (node) node.classList.add("story-visible");
      });
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("story-visible");
          }
        });
      },
      { threshold: 0.22, rootMargin: "0px 0px -8% 0px" }
    );

    storyRefs.current.forEach((node) => {
      if (node) observer.observe(node);
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  const recentDateKeys = useMemo(() => buildRecentDateKeys(7), []);
  const orchestrationDateKeys = useMemo(() => buildRecentDateKeys(orchestrationWindowDays), [orchestrationWindowDays]);

  const planTrend = useMemo(
    () => toTrendData(recentDateKeys, state.plans.map((item) => item.plan_date)),
    [recentDateKeys, state.plans]
  );
  const reflectionTrend = useMemo(
    () => toTrendData(recentDateKeys, state.reflections.map((item) => item.entry_date)),
    [recentDateKeys, state.reflections]
  );
  const analysisTrend = useMemo(
    () => toTrendData(recentDateKeys, state.analyses.map((item) => item.analysis_date)),
    [recentDateKeys, state.analyses]
  );
  const orchestrationTrend = useMemo(
    () =>
      toTrendData(
        orchestrationDateKeys,
        state.orchestrations
          .map((item) => item.created_at?.slice(0, 10))
          .filter((value): value is string => Boolean(value))
      ),
    [orchestrationDateKeys, state.orchestrations]
  );
  const orchestrationPeriodStats = useMemo(
    () => buildOrchestrationPeriodStats(state.orchestrations, orchestrationWindowDays),
    [state.orchestrations, orchestrationWindowDays]
  );
  const previousRunBaseline = orchestrationPeriodStats.previous.runs;
  const runCountDelta = state.orchestrationMetrics.total_runs - previousRunBaseline;
  const previousPartialSuccessRate = toPartialSuccessRate(orchestrationPeriodStats.previous);
  const partialSuccessRateDelta = state.orchestrationMetrics.partial_success_rate - previousPartialSuccessRate;
  const anomalyHints = useMemo(
    () => buildAnomalyHints(orchestrationPeriodStats, orchestrationWindowDays),
    [orchestrationPeriodStats, orchestrationWindowDays]
  );

  const mergedError = [error, orchestrationError].filter(Boolean).join(" ") || null;

  return (
    <PageCard title="Dashboard" description="Personal execution loop at a glance.">
      <section className="hero-obsidian animate-enter">
        <div className="hero-copy">
          <p className="eyebrow">OBSIDIAN-INSPIRED WORKSPACE</p>
          <h3 className="hero-title">Build a second brain for execution, reflection, and technical decisions.</h3>
          <p className="muted">
            Capture daily signals, connect insights, and turn intent into repeatable momentum.
          </p>
          <div className="hero-actions">
            <Link className="nav-link nav-link-active" href="/today">
              Start Today Plan
            </Link>
            <Link className="nav-link" href="/technical-analysis">
              Analyze Incident
            </Link>
          </div>
        </div>
        <div className="hero-glass-stack" aria-hidden="true">
          <div className="glass-layer glass-layer-a" />
          <div className="glass-layer glass-layer-b" />
          <div className="glass-layer glass-layer-c" />
        </div>
      </section>

      {mergedError ? <p className="status status-error">{mergedError}</p> : null}
      {isLoading ? <p className="muted">Loading dashboard data...</p> : null}

      <section className="kpi-grid">
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Saved Daily Plans</p>
          <p className="kpi-value">{state.plans.length}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Saved Reflections</p>
          <p className="kpi-value">{state.reflections.length}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Technical Analyses</p>
          <p className="kpi-value">{state.analyses.length}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Orchestration Runs</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{state.orchestrationMetrics.total_runs}</p>
          <p className={`kpi-delta ${deltaClassName(runCountDelta)}`}>
            {formatSignedInteger(runCountDelta)} vs previous {orchestrationWindowDays}D
          </p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Weekly Active Orchestrations</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{state.orchestrationMetrics.weekly_active_orchestrations}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Partial Success Rate</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{formatPercent(state.orchestrationMetrics.partial_success_rate)}</p>
          <p className={`kpi-delta ${deltaClassName(partialSuccessRateDelta, true)}`}>
            {formatSignedPercentPoint(partialSuccessRateDelta)} vs previous {orchestrationWindowDays}D
          </p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Avg Orchestration Duration</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{formatDurationMs(state.orchestrationMetrics.average_duration_ms)}</p>
        </article>
      </section>

      <section className="graph-filter-row" aria-label="orchestration-window-switcher">
        {DASHBOARD_WINDOW_OPTIONS.map((days) => {
          const active = orchestrationWindowDays === days;
          return (
            <button
              key={days}
              type="button"
              className={active ? "graph-filter-active" : undefined}
              onClick={() => {
                setOrchestrationWindowDays(days);
              }}
              aria-pressed={active}
            >
              {days}D Window
            </button>
          );
        })}
      </section>
      {orchestrationLoading ? <p className="muted">Updating orchestration window...</p> : null}
      <section className="anomaly-hints" aria-label="orchestration-anomaly-hints">
        {anomalyHints.length > 0 ? (
          anomalyHints.map((hint, index) => (
            <p key={`${hint}-${index}`} className="status status-error">
              Anomaly hint: {hint}
            </p>
          ))
        ) : (
          <p className="muted">No orchestration anomalies detected for the selected window.</p>
        )}
      </section>

      <section className="chart-grid">
        <MiniBarTrend title="Planning Activity" subtitle="Daily plans in last 7 days" data={planTrend} />
        <MiniBarTrend
          title="Reflection Activity"
          subtitle="Daily reflections in last 7 days"
          data={reflectionTrend}
          tone="success"
        />
        <MiniBarTrend
          title="Analysis Activity"
          subtitle="Technical analyses in last 7 days"
          data={analysisTrend}
        />
        <MiniLineTrend
          title="Orchestration Activity"
          subtitle={`Workflow orchestrations in last ${orchestrationWindowDays} days`}
          data={orchestrationTrend}
          tone="success"
        />
      </section>

      <section className="graph-grid">
        <KnowledgeGraphPreview />
      </section>

      <section className="story-grid">
        <article
          className="story-step"
          ref={(node) => {
            storyRefs.current[0] = node;
          }}
        >
          <p className="eyebrow">Chapter 01</p>
          <h3>Collect Signals</h3>
          <p className="muted">Track meetings, blockers, and work fragments before context is lost.</p>
        </article>
        <article
          className="story-step"
          ref={(node) => {
            storyRefs.current[1] = node;
          }}
        >
          <p className="eyebrow">Chapter 02</p>
          <h3>Connect Patterns</h3>
          <p className="muted">Surface links between plan quality, reflection quality, and incident pressure.</p>
        </article>
        <article
          className="story-step"
          ref={(node) => {
            storyRefs.current[2] = node;
          }}
        >
          <p className="eyebrow">Chapter 03</p>
          <h3>Act With Clarity</h3>
          <p className="muted">Turn insights into tomorrow&apos;s first action and stronger execution loops.</p>
        </article>
      </section>

      <div className="result-grid">
        <article className="result-block animate-enter">
          <h3>1. Plan The Day</h3>
          <p>Capture tasks, blockers, and meetings to generate a practical execution order.</p>
          <Link className="nav-link" href="/today">
            Open Today Planner
          </Link>
        </article>

        <article className="result-block animate-enter">
          <h3>2. Analyze Technical Issues</h3>
          <p>Turn logs, errors, and snippets into validation steps, fix options, and follow-up tasks.</p>
          <Link className="nav-link" href="/technical-analysis">
            Open Technical Analysis
          </Link>
        </article>

        <article className="result-block animate-enter">
          <h3>3. Reflect And Improve</h3>
          <p>Summarize outcomes, detect patterns, and lock tomorrow&apos;s next actions.</p>
          <Link className="nav-link" href="/reflection">
            Open Reflection
          </Link>
        </article>
      </div>
    </PageCard>
  );
}
