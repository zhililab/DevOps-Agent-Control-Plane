# Core Functionality Check

This document records the current product target and the minimum functionality that must stay green for the DevOps orchestration MVP.

## Current Product Target

- Current release target: deterministic DevOps personal/small-team workflow orchestration MVP.
- Commercial wedge: personal DevOps agent control plane for trusted, replayable, checkpointed, policy-gated workflow execution.
- Primary surfaces: `/orchestrate`, `/orchestrations`, `/dashboard`, `/monetization`, and `/tutorial`.
- Release path: Docker Compose server deployment through `make release-deploy`.
- Public entrypoint: `http://1.117.63.81`.
- Canonical health route: `/health`.

## Core User Flows

- Run a sync orchestration from `/orchestrate` with a signed entitlement token.
- Capture lightweight team/requester/approver metadata on the run without requiring a login system.
- Inspect run replay immediately after the orchestration finishes.
- Navigate to `/orchestrations` and verify persisted run history and step replay.
- Load checkpoint timeline for a run and confirm checkpoint payload hashes verify as valid.
- Submit queued orchestration work, then inspect queue job state, retry/cancel controls, and timeline replay.
- Review dashboard orchestration KPIs and monetization observability fallback states.
- Activate or change a manual subscription on `/monetization`, then confirm usage counters and subject-scoped audit events update.
- Load the same billing subject on `/orchestrate`; an active Pro/Power subscription should issue a signed entitlement token for compatible workflow runs.
- Review Commercial Metrics V2 on `/monetization`: billable work units, policy blocks, top value templates, and anomaly hints should load independently from subscription/profile refreshes.
- Confirm `/dashboard` shows Commercial Work Units and Commercial Policy Blocks from the canonical commercial metrics API.
- Confirm `/monetization` keeps the active subscription visible if usage or audit-feed refreshes are slow or partially unavailable.
- Use `/tutorial` to explain the commercial path from workflow run to replay evidence to plan upgrade.
- Generate and persist daily plans, daily reflections, and technical analysis records.
- Review daily history with accurate `Asia/Shanghai` business dates while preserving UTC audit timestamps.
- Browse reusable knowledge entries, prompt templates, and workflow templates.
- Import or refresh curated orchestration workflow templates for the current DevOps operating loop.
- Confirm selected workflow templates expose their orchestration pattern metadata (`pattern:sequential`, `pattern:maker-checker`, or `pattern:handoff`).
- Confirm selected workflow templates expose policy metadata: required tier, risk level, human approval requirement, allowed tool scopes, and billable work units.
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
- `POST /api/monetization/checkout/manual`
- `POST /api/monetization/cancel`
- `POST /api/monetization/reactivate`

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
- Backfill of historical orchestration records must be idempotent.
- Daily plan/reflection/analysis history must hide `record_source=smoke_check|system` by default and expose it only through `include_system=true`.
- Read-only history endpoints must not create new agent run log records.
- Manual billing UI refreshes profile, usage counters, and commercial audit feed independently; partial failures must not overwrite a successful lifecycle response.

## Query Performance Baseline

- `/api/orchestrations/history` must load step replay records in a single batched query for the page of runs.
- Dashboard trend reads should use `/api/orchestrations/history?include_steps=false&include_integrity=false` when step replay and ledger status details are not rendered.
- Orchestration metrics should use database aggregate queries instead of Python-side full-window scans.
- Orchestration metrics must include billable work units, successful audited workflows, approval blocks, and template policy upgrade blocks.
- Orchestration metrics must include Team Trust KPIs: approved runs, checkpointed runs, and failed jobs needing owner.
- Queue history and queue event timeline reads must keep stable newest-first ordering backed by composite indexes.
- Commercial audit feed reads should use subject-scoped `/api/monetization/events?subject=...` on account pages to avoid global event noise and reduce payload work.
- Commercial Metrics V2 reads should use `/api/monetization/commercial-metrics` with bounded `days=7|30`; subject-scoped account pages should pass `subject`, while dashboard uses the global view.
- `/orchestrate` should warn before submit when the current signed entitlement tier is lower than the selected template policy tier, and should offer a compatible template path for Pro users.
- Global route transition and header preview animations should avoid continuous idle work and respect `prefers-reduced-motion`.

## Non-Blocking Product Modules

- P7 Communication Assistant remains part of the long-term personal assistant vision.
- P8 Weekly Review remains planned, but is not a blocker for the current orchestration MVP.
- k3d/k8s deployment verification remains a follow-up deployment path, not the current release blocker.
