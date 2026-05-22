"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import { formatBusinessTimestamp } from "@/lib/time";
import type { MonetizationEvent, SubscriptionProfile, SubscriptionTier, UsageCounter } from "@/lib/types";

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
    description: "Basic single-step orchestration for evaluation.",
    features: ["25 workflow runs", "25 queued runs", "Single enabled step", "Core replay history"],
  },
  {
    tier: "pro",
    name: "Pro",
    price: "$29",
    description: "Multi-step DevOps agent workflows for daily use.",
    features: ["300 workflow runs", "300 queued runs", "Planner/Analyzer/Reviewer", "Template policy metadata"],
  },
  {
    tier: "power",
    name: "Power",
    price: "$99",
    description: "Audited control-plane workflows with approval gates.",
    features: ["2000 workflow runs", "2000 queued runs", "Policy approval gates", "Commercial work-unit reporting"],
  },
];

const DEFAULT_SUBJECT = "demo-user";

function metricLabel(metric: string): string {
  return metric === "queued_runs" ? "Queued Runs" : "Workflow Runs";
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
  const [subject, setSubject] = useState(DEFAULT_SUBJECT);
  const [profile, setProfile] = useState<SubscriptionProfile | null>(null);
  const [counters, setCounters] = useState<UsageCounter[]>([]);
  const [events, setEvents] = useState<MonetizationEvent[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const activePlan = useMemo(() => PLANS.find((plan) => plan.tier === profile?.tier), [profile]);

  async function loadMonetization(currentSubject = subject) {
    const normalizedSubject = currentSubject.trim() || DEFAULT_SUBJECT;
    setIsLoading(true);
    setError(null);
    try {
      const [profileResponse, usageResponse, eventsResponse] = await Promise.all([
        apiClient.getSubscriptionProfile(normalizedSubject),
        apiClient.listUsageCounters(normalizedSubject),
        apiClient.listMonetizationEvents(25),
      ]);
      setProfile(profileResponse.profile ?? null);
      setCounters(Array.isArray(usageResponse.counters) ? usageResponse.counters : []);
      setEvents(Array.isArray(eventsResponse.events) ? eventsResponse.events : []);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load monetization data.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMonetization(DEFAULT_SUBJECT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubjectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedSubject = subject.trim() || DEFAULT_SUBJECT;
    setSubject(normalizedSubject);
    setStatus(null);
    await loadMonetization(normalizedSubject);
  }

  async function runLifecycleAction(action: string, callback: () => Promise<unknown>, successMessage: string) {
    setBusyAction(action);
    setStatus(null);
    setError(null);
    try {
      await callback();
      await loadMonetization(subject.trim() || DEFAULT_SUBJECT);
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
    <PageCard title="Monetization" description="Subscription, usage, and billing audit controls for the DevOps agent control plane.">
      {status ? <StatusMessage message={status} tone="success" /> : null}
      {error ? <StatusMessage message={error} tone="error" /> : null}
      {isLoading ? <p className="muted">Loading monetization data...</p> : null}

      <form className="monetization-subject-form" onSubmit={onSubjectSubmit}>
        <label htmlFor="subject">Billing Subject</label>
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
              <p className="muted">Activate a plan to create a manual billing profile and usage counters.</p>
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
        <h3>Billing Event Feed</h3>
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
