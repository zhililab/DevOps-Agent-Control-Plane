"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeGraphPreview } from "@/components/charts/KnowledgeGraphPreview";
import { MiniBarTrend } from "@/components/charts/MiniBarTrend";
import { MiniLineTrend } from "@/components/charts/MiniLineTrend";
import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type {
  CommercialMetricsResponse,
  DailyPlanRecord,
  DailyReflectionRecord,
  MonetizationHealthStatus,
  MonetizationObservability,
  MonetizationObservabilityTrendPoint,
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
  monetizationObservability: MonetizationObservability;
  commercialMetrics: CommercialMetricsResponse;
};

const DEFAULT_ORCHESTRATION_METRICS: WorkflowOrchestrationMetrics = {
  period_days: 7,
  total_runs: 0,
  weekly_active_orchestrations: 0,
  partial_success_rate: 0,
  average_duration_ms: 0,
  billable_work_units: 0,
  successful_audited_workflows: 0,
  approval_required_blocks: 0,
  template_policy_upgrade_blocks: 0,
  approved_runs: 0,
  checkpointed_runs: 0,
  failed_jobs_needing_owner: 0,
};

const DEFAULT_MONETIZATION_OBSERVABILITY: MonetizationObservability = {
  period_days: 7,
  kpis: {
    total_revenue_usd: 0,
    paid_runs: 0,
    conversion_rate: 0,
    failed_payment_rate: 0,
  },
  trend: [],
  health: {
    status: "healthy",
    summary: "No monetization health incidents in the selected window.",
    incidents: [],
  },
};

const DEFAULT_COMMERCIAL_METRICS: CommercialMetricsResponse = {
  window_days: 7,
  generated_at: "",
  subject: null,
  subscription_summary: {
    active_subjects: 0,
    profile_count: 0,
    tier_distribution: { free: 0, pro: 0, power: 0 },
    status_distribution: { inactive: 0, active: 0, past_due: 0, canceled: 0 },
  },
  usage_summary: {
    workflow_runs_used: 0,
    workflow_runs_limit: 0,
    queued_runs_used: 0,
    queued_runs_limit: 0,
    usage_subjects: 0,
  },
  plan_usage: {
    workflow_runs_used: 0,
    workflow_runs_limit: 0,
    queued_runs_used: 0,
    queued_runs_limit: 0,
    period_start: null,
    period_end: null,
  },
  commercial_events: [],
  policy_blocks: {
    approval_required: 0,
    upgrade_required: 0,
    quota_exceeded: 0,
    total: 0,
  },
  billable_work_units: {
    total: 0,
    audited_workflows: 0,
    average_per_run: 0,
  },
  top_templates: [],
  trend: [],
  anomaly_hints: [],
};

const DASHBOARD_WINDOW_OPTIONS = [7, 30] as const;
const USD_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDurationMs(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }
  return `${Math.round(value)}ms`;
}

function formatUsd(value: number): string {
  return USD_FORMATTER.format(value);
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
    typeof metrics.average_duration_ms === "number" &&
    typeof metrics.billable_work_units === "number" &&
    typeof metrics.successful_audited_workflows === "number" &&
    typeof metrics.approval_required_blocks === "number" &&
    typeof metrics.template_policy_upgrade_blocks === "number" &&
    typeof metrics.approved_runs === "number" &&
    typeof metrics.checkpointed_runs === "number" &&
    typeof metrics.failed_jobs_needing_owner === "number"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function safeNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return fallback;
}

function safeString(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  return fallback;
}

function parseHealthStatus(value: unknown): MonetizationHealthStatus {
  return value === "warning" || value === "critical" || value === "healthy" ? value : "healthy";
}

function parseTrendPoint(value: unknown): MonetizationObservabilityTrendPoint | null {
  if (!isRecord(value)) return null;
  const date = safeString(value.date, "");
  if (!date) return null;
  return {
    date,
    revenue_usd: safeNumber(value.revenue_usd),
    paid_runs: safeNumber(value.paid_runs),
    conversion_rate: safeNumber(value.conversion_rate),
  };
}

function normalizeMonetizationObservability(
  value: unknown,
  windowDays: number
): { data: MonetizationObservability; valid: boolean } {
  if (!isRecord(value)) {
    return {
      data: { ...DEFAULT_MONETIZATION_OBSERVABILITY, period_days: windowDays },
      valid: false,
    };
  }

  const rootCandidate = isRecord(value.observability) ? value.observability : value;
  const kpisCandidate = isRecord(rootCandidate.kpis) ? rootCandidate.kpis : {};
  const healthCandidate = isRecord(rootCandidate.health) ? rootCandidate.health : {};
  const trendCandidate = Array.isArray(rootCandidate.trend) ? rootCandidate.trend : [];
  const incidents = Array.isArray(healthCandidate.incidents)
    ? healthCandidate.incidents.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];

  const parsed: MonetizationObservability = {
    period_days: safeNumber(rootCandidate.period_days, windowDays),
    kpis: {
      total_revenue_usd: safeNumber(kpisCandidate.total_revenue_usd),
      paid_runs: safeNumber(kpisCandidate.paid_runs),
      conversion_rate: safeNumber(kpisCandidate.conversion_rate),
      failed_payment_rate: safeNumber(kpisCandidate.failed_payment_rate),
    },
    trend: trendCandidate.map(parseTrendPoint).filter((point): point is MonetizationObservabilityTrendPoint => point !== null),
    health: {
      status: parseHealthStatus(healthCandidate.status),
      summary: safeString(
        healthCandidate.summary,
        DEFAULT_MONETIZATION_OBSERVABILITY.health.summary
      ),
      incidents,
    },
  };

  const valid =
    "kpis" in rootCandidate &&
    "trend" in rootCandidate &&
    "health" in rootCandidate &&
    isRecord(rootCandidate.kpis) &&
    Array.isArray(rootCandidate.trend) &&
    isRecord(rootCandidate.health);

  return { data: parsed, valid };
}

function hasCommercialMetricsPayload(value: unknown): value is CommercialMetricsResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value.window_days === "number" &&
    isRecord(value.subscription_summary) &&
    isRecord(value.usage_summary) &&
    isRecord(value.plan_usage) &&
    isRecord(value.policy_blocks) &&
    isRecord(value.billable_work_units) &&
    Array.isArray(value.top_templates) &&
    Array.isArray(value.trend) &&
    Array.isArray(value.anomaly_hints)
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

function healthClassName(status: MonetizationHealthStatus): string {
  if (status === "critical") return "status-error";
  if (status === "warning") return "status-default";
  return "status-success";
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
    monetizationObservability: DEFAULT_MONETIZATION_OBSERVABILITY,
    commercialMetrics: DEFAULT_COMMERCIAL_METRICS,
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
        monetizationObservability: { ...DEFAULT_MONETIZATION_OBSERVABILITY },
        commercialMetrics: { ...DEFAULT_COMMERCIAL_METRICS },
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

      const [metricsResult, historyResult, monetizationResult, commercialMetricsResult] = await Promise.allSettled([
        apiClient.getWorkflowOrchestrationMetrics(orchestrationWindowDays),
        apiClient.listWorkflowOrchestrations({ limit: 200, include_steps: false, include_integrity: false }),
        apiClient.getMonetizationObservability(orchestrationWindowDays),
        apiClient.getCommercialMetrics(orchestrationWindowDays),
      ]);

      const metrics =
        metricsResult.status === "fulfilled" && hasOrchestrationMetricsPayload(metricsResult.value)
          ? metricsResult.value
          : { ...DEFAULT_ORCHESTRATION_METRICS, period_days: orchestrationWindowDays };
      const orchestrations =
        historyResult.status === "fulfilled" && hasItemsPayload(historyResult.value)
          ? historyResult.value.items
          : [];
      const monetization = normalizeMonetizationObservability(
        monetizationResult.status === "fulfilled" ? monetizationResult.value : null,
        orchestrationWindowDays
      );
      const commercialMetrics =
        commercialMetricsResult.status === "fulfilled" && hasCommercialMetricsPayload(commercialMetricsResult.value)
          ? commercialMetricsResult.value
          : { ...DEFAULT_COMMERCIAL_METRICS, window_days: orchestrationWindowDays };

      setState((prev) => ({
        ...prev,
        orchestrationMetrics: metrics,
        orchestrations,
        monetizationObservability: monetization.data,
        commercialMetrics,
      }));

      const failedEndpoints: string[] = [];
      if (metricsResult.status === "rejected" || (metricsResult.status === "fulfilled" && !hasOrchestrationMetricsPayload(metricsResult.value))) {
        failedEndpoints.push("orchestration metrics");
      }
      if (historyResult.status === "rejected" || (historyResult.status === "fulfilled" && !hasItemsPayload(historyResult.value))) {
        failedEndpoints.push("orchestration history");
      }
      if (
        commercialMetricsResult.status === "rejected" ||
        (commercialMetricsResult.status === "fulfilled" && !hasCommercialMetricsPayload(commercialMetricsResult.value))
      ) {
        failedEndpoints.push("commercial metrics");
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
  const monetizationRevenueTrend = useMemo(() => {
    const revenueByDate = new Map<string, number>();
    state.monetizationObservability.trend.forEach((item) => {
      const dateKey = item.date.slice(0, 10);
      revenueByDate.set(dateKey, (revenueByDate.get(dateKey) ?? 0) + item.revenue_usd);
    });
    return orchestrationDateKeys.map((dateKey) => ({
      label: dateKey.slice(5),
      value: revenueByDate.get(dateKey) ?? 0,
    }));
  }, [orchestrationDateKeys, state.monetizationObservability.trend]);
  const commercialWorkUnitTrend = useMemo(() => {
    const workUnitsByDate = new Map<string, number>();
    state.commercialMetrics.trend.forEach((item) => {
      workUnitsByDate.set(item.date.slice(0, 10), item.billable_work_units);
    });
    return orchestrationDateKeys.map((dateKey) => ({
      label: dateKey.slice(5),
      value: workUnitsByDate.get(dateKey) ?? 0,
    }));
  }, [orchestrationDateKeys, state.commercialMetrics.trend]);
  const commercialAnomalyHints = state.commercialMetrics.anomaly_hints.map((hint) => hint.message);

  const mergedError = [error, orchestrationError].filter(Boolean).join(" ") || null;

  return (
    <PageCard
      title="Control Dashboard"
      description="Let enterprises connect agents to CI/CD and incident response without losing control."
    >
      <section className="hero-obsidian animate-enter">
        <div className="hero-copy">
          <p className="eyebrow">ENTERPRISE AGENT CONTROL LAYER</p>
          <h3 className="hero-title">Let teams put agents into CI/CD and incident response without losing control.</h3>
          <p className="muted">
            Gate AI-generated PRs, require human approval for risky releases, and keep replayable ledger, checkpoint,
            and ROI evidence for every agent action.
          </p>
          <div className="hero-actions">
            <Link className="nav-link nav-link-active" href="/orchestrate">
              Run PR Release Gate
            </Link>
            <Link className="nav-link" href="/monetization">
              View Plans
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
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Billable Work Units</p>
          <p className="muted">Template-weighted runs</p>
          <p className="kpi-value">{state.orchestrationMetrics.billable_work_units}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Audited Workflows</p>
          <p className="muted">Successful or partial-success</p>
          <p className="kpi-value">{state.orchestrationMetrics.successful_audited_workflows}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Policy Blocks</p>
          <p className="muted">Approval + tier gates</p>
          <p className="kpi-value">
            {state.orchestrationMetrics.approval_required_blocks +
              state.orchestrationMetrics.template_policy_upgrade_blocks}
          </p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Approved Runs</p>
          <p className="muted">Team-trust actor evidence</p>
          <p className="kpi-value">{state.orchestrationMetrics.approved_runs}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Checkpointed Runs</p>
          <p className="muted">State snapshots persisted</p>
          <p className="kpi-value">{state.orchestrationMetrics.checkpointed_runs}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Jobs Needing Owner</p>
          <p className="muted">Failed queue jobs</p>
          <p className="kpi-value">{state.orchestrationMetrics.failed_jobs_needing_owner}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Revenue</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{formatUsd(state.monetizationObservability.kpis.total_revenue_usd)}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Paid Runs</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{state.monetizationObservability.kpis.paid_runs}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Conversion Rate</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{formatPercent(state.monetizationObservability.kpis.conversion_rate)}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Failed Payment Rate</p>
          <p className="muted">Last {orchestrationWindowDays} days</p>
          <p className="kpi-value">{formatPercent(state.monetizationObservability.kpis.failed_payment_rate)}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Commercial Work Units</p>
          <p className="muted">Commercial Signal</p>
          <p className="kpi-value">{state.commercialMetrics.billable_work_units.total}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Commercial Policy Blocks</p>
          <p className="muted">Approvals + upgrades + quota</p>
          <p className="kpi-value">{state.commercialMetrics.policy_blocks.total}</p>
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
        {[...anomalyHints, ...commercialAnomalyHints].length > 0 ? (
          [...anomalyHints, ...commercialAnomalyHints].map((hint, index) => (
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
        <MiniLineTrend
          title="Monetization Revenue"
          subtitle={`Revenue trend in last ${orchestrationWindowDays} days`}
          data={monetizationRevenueTrend}
        />
        <MiniLineTrend
          title="Commercial Work Units"
          subtitle={`Billable workflow units in last ${orchestrationWindowDays} days`}
          data={commercialWorkUnitTrend}
          tone="success"
        />
        <article className="chart-card animate-enter" aria-label="monetization-health">
          <h3>Monetization Health</h3>
          <p className={`status ${healthClassName(state.monetizationObservability.health.status)}`}>
            {state.monetizationObservability.health.status.toUpperCase()} · {state.monetizationObservability.health.summary}
          </p>
          {state.monetizationObservability.health.incidents.length > 0 ? (
            <ul>
              {state.monetizationObservability.health.incidents.map((incident) => (
                <li key={incident}>{incident}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">No monetization incidents detected.</p>
          )}
        </article>
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
