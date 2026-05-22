"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import { formatBusinessTimestamp } from "@/lib/time";
import type {
  CommercialMetricsResponse,
  MonetizationEvent,
  SubscriptionProfile,
  SubscriptionTier,
  UsageCounter,
} from "@/lib/types";

type Plan = {
  tier: SubscriptionTier;
  name: string;
  price: string;
  description: string;
  features: string[];
};

const PLANS: Plan[] = [
  {
    tier: "free",
    name: "Free",
    price: "$0",
    description: "Evaluate single-step agent workflows with replay evidence.",
    features: ["Try single-step workflows", "25 workflow runs", "25 queued runs", "Core replay history"],
  },
  {
    tier: "pro",
    name: "Pro",
    price: "$29",
    description: "Run multi-step DevOps workflows for daily operations.",
    features: ["Planner/Analyzer/Reviewer", "300 workflow runs", "300 queued runs", "Template policy metadata"],
  },
  {
    tier: "power",
    name: "Power",
    price: "$99",
    description: "Audited control-plane workflows with approval gates.",
    features: ["Approval gates", "Audit evidence", "2000 workflow runs", "Commercial work-unit reporting"],
  },
];

const DEFAULT_SUBJECT = "demo-user";
const BILLING_SUBJECT_STORAGE_KEY = "billing_subject";
const METRICS_WINDOW_OPTIONS = [7, 30] as const;

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

function metricLabel(metric: string): string {
  return metric === "queued_runs" ? "Queued Runs" : "Workflow Runs";
}

function formatLimit(used: number, limit: number): string {
  return limit > 0 ? `${used} / ${limit}` : `${used}`;
}

function eventAction(event: MonetizationEvent): string {
  const action = event.event.action;
  return typeof action === "string" ? action.replaceAll("_", " ") : event.event_kind.replaceAll("_", " ");
}

function eventDetail(event: MonetizationEvent): string {
  const nextTier = event.event.new_tier;
  const tier = event.event.tier;
  const provider = event.event.provider;
  return [typeof nextTier === "string" ? `tier=${nextTier}` : null, typeof tier === "string" ? `tier=${tier}` : null, typeof provider === "string" ? `provider=${provider}` : null]
    .filter(Boolean)
    .join(" · ");
}

export function MonetizationView() {
  const [subject, setSubject] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_SUBJECT;
    return window.localStorage.getItem(BILLING_SUBJECT_STORAGE_KEY)?.trim() || DEFAULT_SUBJECT;
  });
  const [profile, setProfile] = useState<SubscriptionProfile | null>(null);
  const [counters, setCounters] = useState<UsageCounter[]>([]);
  const [events, setEvents] = useState<MonetizationEvent[]>([]);
  const [commercialMetrics, setCommercialMetrics] = useState<CommercialMetricsResponse>(DEFAULT_COMMERCIAL_METRICS);
  const [metricsWindowDays, setMetricsWindowDays] = useState<7 | 30>(7);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadNotice, setLoadNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const activePlan = useMemo(() => PLANS.find((plan) => plan.tier === profile?.tier), [profile]);

  function applyLifecycleResponse(response: {
    profile: SubscriptionProfile;
    counters: UsageCounter[];
    event: MonetizationEvent;
  }) {
    setProfile(response.profile);
    setCounters(Array.isArray(response.counters) ? response.counters : []);
    setEvents((currentEvents) => [
      response.event,
      ...currentEvents.filter((currentEvent) => currentEvent.id !== response.event.id),
    ].slice(0, 25));
  }

  function loadFailureMessage(failures: string[]): string {
    if (failures.length === 0) return "";
    if (failures.length >= 4) {
      return "Commercial data could not refresh. Showing the latest subscription update when available.";
    }
    return `Commercial refresh partially completed. Showing latest available data; missing: ${failures.join(", ")}.`;
  }

  async function loadMonetization(
    currentSubject = subject,
    options: {
      fallbackProfile?: SubscriptionProfile | null;
      fallbackCounters?: UsageCounter[];
      fallbackEvent?: MonetizationEvent;
      fallbackMetrics?: CommercialMetricsResponse;
    } = {}
  ) {
    const normalizedSubject = currentSubject.trim() || DEFAULT_SUBJECT;
    setIsLoading(true);
    setError(null);
    setLoadNotice(null);
    try {
      const [profileResult, usageResult, eventsResult, metricsResult] = await Promise.allSettled([
        apiClient.getSubscriptionProfile(normalizedSubject),
        apiClient.listUsageCounters(normalizedSubject),
        apiClient.listMonetizationEvents(25, normalizedSubject),
        apiClient.getCommercialMetrics(metricsWindowDays, normalizedSubject),
      ]);

      const failures: string[] = [];
      if (profileResult.status === "fulfilled") {
        setProfile(profileResult.value.profile ?? options.fallbackProfile ?? null);
      } else {
        failures.push("subscription profile");
      }

      if (usageResult.status === "fulfilled") {
        const nextCounters = Array.isArray(usageResult.value.counters) ? usageResult.value.counters : [];
        setCounters(nextCounters.length > 0 ? nextCounters : options.fallbackCounters ?? []);
      } else {
        failures.push("usage counters");
      }

      if (eventsResult.status === "fulfilled") {
        const nextEvents = Array.isArray(eventsResult.value.events) ? eventsResult.value.events : [];
        if (nextEvents.length > 0 || !options.fallbackEvent) {
          setEvents(nextEvents);
        } else {
          setEvents((currentEvents) => [
            options.fallbackEvent as MonetizationEvent,
            ...currentEvents.filter((currentEvent) => currentEvent.id !== options.fallbackEvent?.id),
          ].slice(0, 25));
        }
      } else {
        failures.push("commercial audit feed");
      }

      if (metricsResult.status === "fulfilled") {
        setCommercialMetrics(metricsResult.value);
      } else {
        setCommercialMetrics(options.fallbackMetrics ?? commercialMetrics);
        failures.push("commercial metrics");
      }

      if (failures.length > 0) {
        const hasDisplayableProfile = Boolean(options.fallbackProfile || profile?.subject === normalizedSubject);
        const message = loadFailureMessage(failures);
        if (profileResult.status === "rejected" && !hasDisplayableProfile) {
          setError(profileResult.reason instanceof Error ? profileResult.reason.message : message);
        } else {
          setLoadNotice(message);
        }
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load monetization data.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMonetization(subject);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metricsWindowDays]);

  async function onSubjectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    setSubject(normalizedSubject);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(BILLING_SUBJECT_STORAGE_KEY, normalizedSubject);
    }
    setStatus(null);
    await loadMonetization(normalizedSubject);
  }

  async function runLifecycleAction(
    action: string,
    callback: () => Promise<{ profile: SubscriptionProfile; counters: UsageCounter[]; event: MonetizationEvent }>,
    successMessage: string
  ) {
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    setSubject(normalizedSubject);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(BILLING_SUBJECT_STORAGE_KEY, normalizedSubject);
    }
    setBusyAction(action);
    setStatus(null);
    setError(null);
    setLoadNotice(null);
    try {
      const response = await callback();
      applyLifecycleResponse(response);
      await loadMonetization(normalizedSubject, {
        fallbackProfile: response.profile,
        fallbackCounters: response.counters,
        fallbackEvent: response.event,
        fallbackMetrics: commercialMetrics,
      });
      setStatus(successMessage);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Subscription action failed.");
    } finally {
      setBusyAction(null);
    }
  }

  function activatePlan(tier: SubscriptionTier) {
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    void runLifecycleAction(
      `activate-${tier}`,
      () => apiClient.startManualCheckout({ subject: normalizedSubject, target_tier: tier }),
      `${tier.toUpperCase()} subscription is active.`
    );
  }

  function cancelPlan() {
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    void runLifecycleAction(
      "cancel",
      () => apiClient.cancelSubscription(normalizedSubject),
      "Cancellation is scheduled at period end."
    );
  }

  function reactivatePlan() {
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    void runLifecycleAction(
      "reactivate",
      () => apiClient.reactivateSubscription(normalizedSubject),
      "Subscription reactivated."
    );
  }

  return (
    <PageCard title="Plans & Usage" description="Commercial plans, usage counters, and audit controls for the DevOps agent control plane.">
      {status ? <StatusMessage message={status} tone="success" /> : null}
      {error ? <StatusMessage message={error} tone="error" /> : null}
      {loadNotice ? <StatusMessage message={loadNotice} /> : null}
      {isLoading ? <p className="muted">Loading monetization data...</p> : null}

      <section className="monetization-hero" aria-label="commercial-mvp-summary">
        <div>
          <p className="eyebrow">COMMERCIAL MVP</p>
          <h3>Turn trusted DevOps runs into metered plans.</h3>
          <p className="muted">
            Manual Billing V1 keeps the launch surface simple: plan state, usage counters, and audit events stay visible
            without introducing a payment provider yet.
          </p>
          <div className="monetization-pill-row" aria-label="commercial-control-loop">
            <span>Plan</span>
            <span>Usage</span>
            <span>Audit</span>
          </div>
        </div>
        <aside className="monetization-status-panel" aria-label="current-commercial-state">
          <span>Current Plan</span>
          <strong>{profile ? `${profile.tier.toUpperCase()} · ${profile.status}` : "No active plan"}</strong>
          <p>
            {profile
              ? activePlan?.description ?? "Manual subscription profile is active."
              : "Choose Free, Pro, or Power to begin commercial tracking."}
          </p>
        </aside>
      </section>

      <form className="monetization-subject-form monetization-toolbar" onSubmit={onSubjectSubmit}>
        <label htmlFor="subject">Account Subject</label>
        <div className="inline-form-row">
          <input id="subject" value={subject} onChange={(event) => setSubject(event.target.value)} />
          <button type="submit">Load Account</button>
        </div>
      </form>

      <section className="commercial-summary" aria-label="subscription-summary">
        <article className="result-block">
          <p className="eyebrow">Current Subscription</p>
          {profile ? (
            <>
              <h3>
                {profile.tier.toUpperCase()} · {profile.status}
              </h3>
              <p>{activePlan?.description ?? "Manual subscription profile is active."}</p>
              <p className="muted">
                Provider: {profile.billing_provider} · Updated: {formatBusinessTimestamp(profile.updated_at)}
              </p>
              {profile.current_period_end ? (
                <p className="muted">Period ends: {formatBusinessTimestamp(profile.current_period_end)}</p>
              ) : null}
              {profile.cancel_at_period_end ? (
                <p className="status status-error">Cancellation pending at period end.</p>
              ) : null}
            </>
          ) : (
            <>
              <h3>No subscription profile</h3>
              <p className="muted">Choose a plan to start tracking usage and billing events.</p>
            </>
          )}
        </article>

        <article className="result-block">
          <p className="eyebrow">Usage Counters</p>
          {counters.length > 0 ? (
            <div className="usage-counter-grid">
              {counters.map((counter) => (
                <div className="usage-counter" key={counter.id}>
                  <strong>{metricLabel(counter.metric)}</strong>
                  <span>
                    {counter.used} / {counter.limit}
                  </span>
                  <small>
                    {counter.period_start} - {counter.period_end}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No counters yet.</p>
          )}
        </article>
      </section>

      <section className="commercial-metrics-panel" aria-label="commercial-metrics">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Commercial Metrics V2</p>
            <h3>Paid workflow signal</h3>
          </div>
          <div className="graph-filter-row compact-controls" aria-label="commercial-metrics-window">
            {METRICS_WINDOW_OPTIONS.map((days) => {
              const active = metricsWindowDays === days;
              return (
                <button
                  key={days}
                  type="button"
                  className={active ? "graph-filter-active" : undefined}
                  onClick={() => setMetricsWindowDays(days)}
                  aria-pressed={active}
                >
                  {days}D
                </button>
              );
            })}
          </div>
        </div>
        <div className="commercial-metric-grid">
          <article className="result-block">
            <p className="eyebrow">Billable Work Units</p>
            <h3>{commercialMetrics.billable_work_units.total}</h3>
            <p className="muted">
              {commercialMetrics.billable_work_units.audited_workflows} audited workflow(s) · avg{" "}
              {commercialMetrics.billable_work_units.average_per_run}
            </p>
          </article>
          <article className="result-block">
            <p className="eyebrow">Usage</p>
            <h3>{formatLimit(commercialMetrics.usage_summary.workflow_runs_used, commercialMetrics.usage_summary.workflow_runs_limit)}</h3>
            <p className="muted">
              Workflow runs · queued{" "}
              {formatLimit(commercialMetrics.usage_summary.queued_runs_used, commercialMetrics.usage_summary.queued_runs_limit)}
            </p>
          </article>
          <article className="result-block">
            <p className="eyebrow">Policy Blocks</p>
            <h3>{commercialMetrics.policy_blocks.total}</h3>
            <p className="muted">
              approvals {commercialMetrics.policy_blocks.approval_required} · upgrades{" "}
              {commercialMetrics.policy_blocks.upgrade_required}
            </p>
          </article>
          <article className="result-block">
            <p className="eyebrow">Active Subjects</p>
            <h3>{commercialMetrics.subscription_summary.active_subjects}</h3>
            <p className="muted">
              Free {commercialMetrics.subscription_summary.tier_distribution.free} · Pro{" "}
              {commercialMetrics.subscription_summary.tier_distribution.pro} · Power{" "}
              {commercialMetrics.subscription_summary.tier_distribution.power}
            </p>
          </article>
        </div>
        {commercialMetrics.anomaly_hints.length > 0 ? (
          <div className="status-stack">
            {commercialMetrics.anomaly_hints.map((hint) => (
              <StatusMessage
                key={`${hint.code}-${hint.message}`}
                tone={hint.severity === "critical" ? "error" : undefined}
                message={hint.message}
              />
            ))}
          </div>
        ) : (
          <p className="muted">No commercial anomalies detected in this window.</p>
        )}
        <div className="commercial-summary">
          <article className="result-block">
            <h3>Top Value Templates</h3>
            {commercialMetrics.top_templates.length > 0 ? (
              <div className="event-feed">
                {commercialMetrics.top_templates.map((template) => (
                  <article className="event-row" key={`${template.template_id ?? "adhoc"}-${template.template_name}`}>
                    <div>
                      <strong>{template.template_name}</strong>
                      <p className="muted">
                        {template.required_tier} · {template.risk_level} ·{" "}
                        {template.approval_required ? "approval required" : "approval optional"}
                      </p>
                    </div>
                    <span>{template.billable_work_units} wu</span>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">No billable workflow templates yet.</p>
            )}
          </article>
          <article className="result-block">
            <h3>Commercial Events</h3>
            {commercialMetrics.commercial_events.length > 0 ? (
              <div className="usage-counter-grid">
                {commercialMetrics.commercial_events.map((event) => (
                  <div className="usage-counter" key={event.action}>
                    <strong>{event.action}</strong>
                    <span>{event.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No commercial lifecycle events in this window.</p>
            )}
          </article>
        </div>
      </section>

      <section className="pricing-grid" aria-label="pricing-plans">
        {PLANS.map((plan) => {
          const isCurrent = profile?.tier === plan.tier;
          return (
            <article className={`pricing-card ${isCurrent ? "pricing-card-active" : ""}`} key={plan.tier}>
              <p className="eyebrow">{plan.name}</p>
              <h3>{plan.price}<span className="muted">/mo</span></h3>
              <p>{plan.description}</p>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() => activatePlan(plan.tier)}
                aria-label={`Activate ${plan.name}`}
              >
                {busyAction === `activate-${plan.tier}` ? "Working..." : isCurrent ? "Refresh Plan" : `Activate ${plan.name}`}
              </button>
            </article>
          );
        })}
      </section>

      <div className="button-row">
        <button type="button" onClick={cancelPlan} disabled={busyAction !== null || !profile || profile.cancel_at_period_end}>
          {busyAction === "cancel" ? "Working..." : "Cancel At Period End"}
        </button>
        <button type="button" onClick={reactivatePlan} disabled={busyAction !== null || !profile?.cancel_at_period_end}>
          {busyAction === "reactivate" ? "Working..." : "Reactivate"}
        </button>
      </div>

      <section className="result-block" aria-label="monetization-event-feed">
        <h3>Commercial Audit Feed</h3>
        {events.length > 0 ? (
          <div className="event-feed">
            {events.map((event) => (
              <article className="event-row" key={event.id}>
                <div>
                  <strong>{eventAction(event)}</strong>
                  <p className="muted">{eventDetail(event) || event.event_kind}</p>
                </div>
                <span>{formatBusinessTimestamp(event.created_at)}</span>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No monetization events yet.</p>
        )}
      </section>
    </PageCard>
  );
}
