"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeGraphPreview } from "@/components/charts/KnowledgeGraphPreview";
import { MiniBarTrend } from "@/components/charts/MiniBarTrend";
import { PageCard } from "@/components/ui/PageCard";
import { apiClient } from "@/lib/api";
import type {
  DailyPlanRecord,
  DailyReflectionRecord,
  TechnicalAnalysisRecord,
  WorkflowOrchestrationMetrics,
} from "@/lib/types";

type DashboardState = {
  plans: DailyPlanRecord[];
  reflections: DailyReflectionRecord[];
  analyses: TechnicalAnalysisRecord[];
  orchestrationMetrics: WorkflowOrchestrationMetrics;
};

const DEFAULT_ORCHESTRATION_METRICS: WorkflowOrchestrationMetrics = {
  period_days: 7,
  total_runs: 0,
  weekly_active_orchestrations: 0,
  partial_success_rate: 0,
  average_duration_ms: 0,
};

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
  const result: string[] = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i -= 1) {
    const current = new Date(now);
    current.setDate(now.getDate() - i);
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

export function DashboardView() {
  const [state, setState] = useState<DashboardState>({
    plans: [],
    reflections: [],
    analyses: [],
    orchestrationMetrics: DEFAULT_ORCHESTRATION_METRICS,
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [recentDateKeys, setRecentDateKeys] = useState<string[]>([]);
  const storyRefs = useRef<Array<HTMLElement | null>>([]);

  useEffect(() => {
    setRecentDateKeys(buildRecentDateKeys(7));

    async function load() {
      const [plansResult, reflectionsResult, analysesResult, orchestrationMetricsResult] = await Promise.allSettled([
        apiClient.listDailyPlans(),
        apiClient.listDailyReflections(),
        apiClient.listTechnicalAnalyses(),
        apiClient.getWorkflowOrchestrationMetrics(7),
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
      const orchestrationMetrics =
        orchestrationMetricsResult.status === "fulfilled" &&
        hasOrchestrationMetricsPayload(orchestrationMetricsResult.value)
          ? orchestrationMetricsResult.value
          : DEFAULT_ORCHESTRATION_METRICS;

      const nextState: DashboardState = {
        plans,
        reflections,
        analyses,
        orchestrationMetrics,
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
      if (
        orchestrationMetricsResult.status === "rejected" ||
        (orchestrationMetricsResult.status === "fulfilled" &&
          !hasOrchestrationMetricsPayload(orchestrationMetricsResult.value))
      ) {
        failedEndpoints.push("orchestration metrics");
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

      {error ? <p className="status status-error">{error}</p> : null}
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
          <p className="kpi-label">Weekly Active Orchestrations</p>
          <p className="kpi-value">{state.orchestrationMetrics.weekly_active_orchestrations}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Partial Success Rate</p>
          <p className="kpi-value">{formatPercent(state.orchestrationMetrics.partial_success_rate)}</p>
        </article>
        <article className="kpi-card animate-enter">
          <p className="kpi-label">Avg Orchestration Duration</p>
          <p className="kpi-value">{formatDurationMs(state.orchestrationMetrics.average_duration_ms)}</p>
        </article>
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
