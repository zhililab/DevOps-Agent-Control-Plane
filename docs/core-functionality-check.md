# Core Functionality Check

This document records the current product target and the minimum functionality that must stay green for the DevOps orchestration MVP.

## Current Product Target

- Current release target: deterministic DevOps personal/small-team workflow orchestration MVP.
- Commercial wedge: enterprise agent execution trust control layer for trusted, replayable, checkpointed, policy-gated CI/CD and incident-response workflows.
- Primary buyer surfaces: `/orchestrate`, `/orchestrations`, `/dashboard`, `/monetization`, and `/tutorial`.
- Interview quality-proof surface: `/evaluation`.
- Release path: Docker Compose server deployment through `make release-deploy`.
- Public entrypoint: `http://1.117.63.81`.
- Canonical health route: `/health`.

## Core User Flows

- Run a sync orchestration from `/orchestrate` with a signed entitlement token.
- Run `AI-generated PR Release Gate` with PR diff summary, CI logs, change risk, deployment environment, Power entitlement, and explicit human approval.
- Capture Real PR/CI Adapter V1 context: PR URL, diff summary, CI log summary, target environment, and change risk.
- Confirm the release gate returns `approve`, `block`, or `needs human review` with evidence, risk, and next action.
- Confirm the release gate response includes run-level ROI evidence: review time saved, audit time saved, blocked risk count/value, billable work units, assumptions, and estimated customer value.
- Capture lightweight team/requester/approver metadata on the run without requiring a login system.
- Inspect run replay immediately after the orchestration finishes.
- Navigate to `/orchestrations` and verify persisted run history and step replay.
- Confirm the run history reads as an audit report with requester/approver, policy gate, queue timeline, step evidence, checkpoint hash, billable work units, and blocked risk.
- Confirm the audit report shows ROI Evidence with estimated value, time saved, blocked risk value, and transparent assumptions.
- Load checkpoint timeline for a run and confirm checkpoint payload hashes verify as valid.
- Submit queued orchestration work, then inspect queue job state, retry/cancel controls, and timeline replay.
- Review dashboard orchestration KPIs and monetization observability fallback states.
- Activate or change a manual subscription on `/monetization`, then confirm usage counters and subject-scoped audit events update.
- Load the same billing subject on `/orchestrate`; an active Pro/Power subscription should issue a signed entitlement token for compatible workflow runs.
- Review Commercial Signal on `/monetization`: billing-period Plan Usage, billable work units, 7D/30D activity, policy blocks, top value templates, and anomaly hints should load independently from subscription/profile refreshes.
- Confirm Commercial Signal shows ROI summary: estimated customer value, review/audit time saved, blocked risk value, ROI-backed runs, and value by template.
- Export redacted evidence from `/orchestrations` and confirm the Markdown bundle includes PR/CI context, policy gate, step replay, ledger/checkpoint status, and ROI evidence.
- Confirm `/dashboard` shows Commercial Work Units and Commercial Policy Blocks from the canonical commercial metrics API.
- Confirm `/monetization` keeps the active subscription visible if usage or audit-feed refreshes are slow or partially unavailable.
- Use `/tutorial` to explain the commercial path from workflow run to replay evidence to plan upgrade.
- Use `/tutorial` Pilot Dataset cards to load one of five fixed buyer scenarios into `/orchestrate?scenario=<id>`.
- Confirm `/tutorial` behaves as a guided pilot console: progress count, buyer review status, next scenario CTA, and no one-click run-all path.
- Confirm `/orchestrate` can load a pilot scenario and populate PR/CI adapter context, daily context, technical input, reflection input, approval state, and recommended template.
- Confirm the missing-approval scenario returns `409` until approval is explicitly confirmed.
- Confirm `/orchestrate?scenario=missing-approval` frames the first `409` as an expected policy block and provides a confirm-approval-and-rerun path.
- Confirm `/monetization` shows `Pilot Readiness`: completed runs, evidence-exportable runs, ledger-valid runs, checkpointed runs, approval-required runs, blocked/needs-review runs, metadata completeness, and estimated pilot value.
- Confirm `/monetization` shows Buyer Review Status and all five pilot scenario statuses grouped as completed, missing, or needing evidence.
- Confirm `/monetization` shows `Why Power` using actual policy/approval/evidence/ROI data, not hard-coded fake values.
- Confirm `/monetization` can copy/download the redaction-safe Pilot Closeout report.
- Confirm `/dashboard` shows `Pilot Ready` as a buyer-facing KPI.
- Open `/evaluation` and confirm provider readiness never exposes credentials.
- Run the versioned 25-case PR/CI set in deterministic mode, then compare expected and actual decisions with accuracy, false-positive, and false-negative counts.
- When a rotated provider key and model are configured, run the same fixed set in live mode and inspect model, prompt version, token, latency, and estimated-cost records.
- Append accept/reject/correct human feedback and confirm feedback metrics are calculated from persisted review records.
- Record observed Baseline and Pilot measurements and confirm they remain visibly separate from directional ROI assumptions.
- Generate and persist daily plans, daily reflections, and technical analysis records.
- Review daily history with accurate `Asia/Shanghai` business dates while preserving UTC audit timestamps.
- Browse reusable knowledge entries, prompt templates, and workflow templates.
- Import or refresh curated orchestration workflow templates for the current DevOps operating loop.
- Confirm selected workflow templates expose their orchestration pattern metadata (`pattern:sequential`, `pattern:maker-checker`, or `pattern:handoff`).
- Confirm selected workflow templates expose policy metadata: required tier, risk level, human approval requirement, allowed tool scopes, and billable work units.
- Confirm `AI-generated PR Release Gate` is a Power, high-risk, approval-required template with `ci-cd-release-gate` tool scope and 8 billable work units.
- Confirm approval-required templates cannot run until explicit human approval is submitted.
- Verify orchestration history ledger integrity for a run and confirm event count/status.
- Confirm `/orchestrations` keeps ledger valid status and checkpoint count visible after reload/redeploy.

## Core API Surface

- `GET /health`
- `POST /api/plans/daily`
- `POST /api/reflections/daily`
- `POST /api/analysis/technical`
- `POST /api/orchestrations/run`
- `GET /api/orchestrations/history`
- `GET /api/orchestrations/{id}`
- `GET /api/orchestrations/{id}/history-events`
- `GET /api/orchestrations/{id}/checkpoints`
- `GET /api/orchestrations/{id}/evidence`
- `GET /api/orchestrations/pilot-scenarios`
- `GET /api/orchestrations/metrics?days=...`
- `POST /api/orchestrations/queue/run`
- `GET /api/orchestrations/queue/history`
- `GET /api/orchestrations/queue/{job_id}`
- `POST /api/orchestrations/queue/{job_id}/retry`
- `POST /api/orchestrations/queue/{job_id}/cancel`
- `GET /api/orchestrations/templates/init/json`
- `POST /api/orchestrations/templates/import/builtin`
- `GET /api/observability/monetization?days=...`
- `GET /api/monetization/profile|usage|events`
- `GET /api/monetization/entitlement?subject=...`
- `GET /api/monetization/commercial-metrics?days=7|30&subject=...`
- `GET /api/monetization/pilot-report?days=7|30&subject=...&team_subject=...`
- `GET /api/monetization/pilot-closeout?days=7|30&subject=...&team_subject=...`
- `POST /api/monetization/checkout/manual`
- `POST /api/monetization/cancel`
- `POST /api/monetization/reactivate`
- `GET /api/evaluations/provider-status`
- `GET /api/evaluations/cases`
- `POST /api/evaluations/runs`
- `GET /api/evaluations/runs/latest`
- `GET /api/evaluations/invocations`
- `POST /api/evaluations/feedback`
- `GET /api/evaluations/feedback-summary`
- `POST /api/evaluations/pilot-measurements`
- `GET /api/evaluations/pilot-comparison`

## Security And Robustness Baseline

- Production orchestration actions require signed `X-Entitlement`.
- Legacy `X-Subscription-Tier` is disabled in production.
- Free tier must reject multi-step orchestration with `403`.
- Template required tier must reject lower-tier runs with `403`.
- Approval-required templates must reject unapproved sync/queue runs with `409`.
- Missing entitlement must reject orchestration with `401`.
- Oversized structured payloads must reject with `422` or gateway `413`.
- API rate limit must return `429` with `Retry-After`.
- Gateway responses must include baseline security headers.
- `X-Powered-By` must not be exposed by the frontend.
- `/api/health` must not become a second health route; `/health` remains canonical.
- Orchestration ledger payload hashes must verify against canonical JSON snapshots.
- Workflow checkpoint payload hashes must verify against canonical JSON snapshots.
- Orchestration and queue audit payloads must redact tokens, passwords, secrets, and raw entitlement strings.
- Pilot scenarios and pilot readiness payloads must not include raw entitlement tokens, passwords, secrets, or private credentials.
- Pilot closeout Markdown and JSON payloads must not include raw entitlement tokens, passwords, secrets, or private credentials.
- Backfill of historical orchestration records must be idempotent.
- Daily plan/reflection/analysis history must hide `record_source=smoke_check|system` by default and expose it only through `include_system=true`.
- Read-only history endpoints must not create new agent run log records.
- Manual billing UI refreshes profile, usage counters, and commercial audit feed independently; partial failures must not overwrite a successful lifecycle response.
- Manual checkout must renew an expired active profile before entitlement issuance while preserving historical counters and audit records.
- LLM API keys must remain environment-only; provider status, invocation records, errors, evaluation results, and request hashes must not expose raw credentials.
- Production evaluation runs, feedback, and Pilot measurement writes must require `X-Evaluation-Access`; the access secret must be independent from the provider API key and remain environment-only.
- Ordinary orchestration runs must not invoke the optional LLM provider unless `use_llm_provider=true` is explicitly submitted.
- Release gates must clear production Provider credentials from local test subprocesses so E2E cannot consume real model quota.
- Provider output remains advisory evidence. A provider timeout, malformed response, or disagreement must not replace the deterministic policy-gate decision.

## Query Performance Baseline

- `/api/orchestrations/history` must load step replay records in a single batched query for the page of runs.
- Dashboard trend reads should use `/api/orchestrations/history?include_steps=false&include_integrity=false` when step replay and ledger status details are not rendered.
- Orchestration metrics should use database aggregate queries instead of Python-side full-window scans.
- Orchestration metrics must include billable work units, successful audited workflows, approval blocks, and template policy upgrade blocks.
- Orchestration metrics must include Team Trust KPIs: approved runs, checkpointed runs, and failed jobs needing owner.
- Release-gate ROI evidence should be visible on each orchestration read/history response and in `/orchestrations`; Commercial Signal also aggregates ROI into buyer-facing estimated value, review time saved, blocked risk value, and value by template.
- Pilot Readiness should reuse bounded 7D/30D windows and existing orchestration, ledger, checkpoint, and ROI data; it must not introduce full-table scans or new billing tables.
- Pilot Readiness `scenario_completion` should derive progress from existing orchestration request metadata and evidence state; it must not create a persistent scenario table.
- Pilot Closeout should be a read-only projection over Pilot Readiness plus Commercial Signal data; repeated report reads must not mutate usage counters or trigger backfill churn.
- Queue history and queue event timeline reads must keep stable newest-first ordering backed by composite indexes.
- Commercial audit feed reads should use subject-scoped `/api/monetization/events?subject=...` on account pages to avoid global event noise and reduce payload work.
- Commercial Signal reads should use `/api/monetization/commercial-metrics` with bounded `days=7|30`; subject-scoped account pages should pass `subject`, while dashboard uses the global view. Billing-period Plan Usage comes from `usage_counters`; 7D/30D activity comes from usage audit logs; ROI summary comes from run-level release-gate evidence.
- `/orchestrate` should warn before submit when the current signed entitlement tier is lower than the selected template policy tier, and should offer a compatible template path for Pro users.
- Global route transition and header preview animations should avoid continuous idle work and respect `prefers-reduced-motion`.
- Evaluation case and invocation reads must use bounded result sets with stable newest-first ordering; fixed-set execution must never run implicitly from dashboard or smoke reads.

## Non-Blocking Product Modules

- P7 Communication Assistant remains part of the long-term personal assistant vision.
- P8 Weekly Review remains planned, but is not a blocker for the current orchestration MVP.
- k3d/k8s deployment verification remains a follow-up deployment path, not the current release blocker.
