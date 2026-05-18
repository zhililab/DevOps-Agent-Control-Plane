# MVP Architecture Notes

## System Shape
- Frontend: Next.js app router with TypeScript views under `frontend/app` and feature components under `frontend/features`.
- Backend: FastAPI app with modular routers under `backend/app/api`.
- Persistence: SQLAlchemy models with Alembic migrations; SQLite remains the fast local default and PostgreSQL is the deploy target.
- API prefix: backend routes are mounted under `/api` by `backend/app/main.py`.
- Local boundary: the product still avoids autonomous third-party actions; user-triggered workflows write deterministic, inspectable records.

## Backend Modules
- Core MVP routers: `profile`, `plans`, `reflections`, `technical_analysis`, `tasks`.
- Reuse routers: `knowledge`, `templates`.
- Orchestration routers: `orchestrations`, including sync runs, queue runs, replay/history, metrics, entitlement bootstrap, and workflow templates.
- Observability router: `observability`, currently exposing monetization aggregation at `/api/observability/monetization`.
- Services keep business logic out of routers: planning/reflection/analysis services produce deterministic outputs; orchestration, queue, entitlement, knowledge, and template services own their respective workflows.

## Persistence Model
- Daily-use records: `UserProfile`, `Task`, `DailyPlan`, `ReflectionEntry`, `TechnicalAnalysis`, `AgentRunLog`.
- Knowledge/template records: `NoteEntry`, `PromptTemplate`.
- Orchestration records: `WorkflowOrchestration`, `WorkflowStepRun`, `WorkflowTemplate`.
- Queue records: `WorkflowQueueJob`, `WorkflowQueueEvent`.
- Monetization records: `SubscriptionProfile`, `UsageCounter`, `MonetizationEvent`.
- Compatibility note: monetization observability currently reads the active runtime audit trail from `AgentRunLog` entries with `monetization.*` task types; the monetization tables are present for the fuller billing/audit API surface.

## Orchestration
- The orchestration API supports deterministic multi-agent workflows through Planner, Analyzer, and Reviewer steps.
- A run request can provide explicit steps or reference a `WorkflowTemplate`; otherwise the service falls back to the default Planner/Analyzer/Reviewer sequence.
- Each run writes a `WorkflowOrchestration` row plus ordered `WorkflowStepRun` rows.
- Step outputs are structured as audit blocks with `conclusion`, `evidence`, `risk`, and `next_action`.
- Partial success is first-class: a failed Analyzer step records a failed step and fallback action, then the workflow can still return a `partial_success` orchestration.
- Replay/history is driven from persisted step records rather than regenerated text.
- Optional persistence can promote orchestration summaries into `NoteEntry` knowledge records and `PromptTemplate` replay prompts.

## Queue Lifecycle
- Async orchestration starts at `POST /api/orchestrations/queue/run`.
- Queue jobs use statuses: `queued`, `running`, `succeeded`, `failed`, `canceled`.
- Queue job attempts, retry limits, cancel requests, linked orchestration IDs, and error messages are stored on `WorkflowQueueJob`.
- `WorkflowQueueEvent` stores an append-only event timeline for queued, started, retry requested, cancel requested, succeeded, failed, and canceled transitions.
- Retry is allowed only for failed or canceled jobs and respects `max_attempts`.
- Cancel is idempotency-aware by state: queued jobs move directly to canceled, running jobs set `cancel_requested`, and terminal jobs return a deterministic conflict.
- The `/orchestrations` UI lists queue jobs and renders timeline replay; retry/cancel controls currently remain in `/orchestrate`.

## Entitlement And Tier Gates
- Orchestration calls resolve tier from signed `X-Entitlement` tokens when present.
- In production, signed entitlement is required and legacy `X-Subscription-Tier` fallback is disabled.
- In non-production, `X-Subscription-Tier` is honored only when `APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK=true`.
- `APP_ENTITLEMENT_REQUIRED=true` forces signed entitlement in every environment.
- Signed tokens include tier, user ID, expiry, and an HMAC signature using `APP_ENTITLEMENT_SECRET`.
- Token tier is authoritative when both signed and legacy headers are provided.
- Free tier is limited to one enabled orchestration step; pro and power support the current three-step workflow.
- Quota checks are tier-specific and currently count recent `monetization.usage_recorded` audit events by endpoint and subject.

## Monetization Observability
- Runtime monetization decisions write structured `AgentRunLog` events such as capability checks, quota checks, quota exceeded, upgrade-required blocks, and usage recorded.
- Canonical aggregation route: `GET /api/observability/monetization?days=7|30`.
- Dedicated monetization read routes expose stored billing/audit tables:
  - `GET /api/monetization/profile?subject=...` returns the latest profile for a subject or `profile: null`.
  - `GET /api/monetization/usage?subject=...` returns deterministic usage counter history for the subject.
  - `GET /api/monetization/events?limit=...` returns newest-first monetization audit events.
- The aggregation reports active subjects, runs by tier, quota hit rate, upgrade intent count, queue success rate, p95 queue latency, and top failure reasons.
- Orchestration metrics remain separate at `GET /api/orchestrations/metrics?days=...` and report run volume, weekly active orchestration count, partial success rate, and average duration.
- Frontend monetization observability now calls the canonical backend route through `frontend/lib/api.ts`.
- Current gap: runtime monetization decisions are still primarily written to `AgentRunLog`; the dedicated monetization tables are exposed for read/audit workflows but are not yet the write source for orchestration quota and usage decisions.

## Knowledge And Templates
- `NoteEntry` stores durable knowledge with normalized tags and updated-at ordering.
- `PromptTemplate` stores reusable prompt bodies with normalized tags and supports JSON/SQL bootstrap import.
- Built-in starter prompt templates live in `backend/app/bootstrap/prompt_templates_v1.json`.
- Local helper commands `make templates-import-json` and `make templates-import-sql` call the import APIs.
- `WorkflowTemplate` is separate from prompt templates: it stores orchestration step definitions for replayable multi-agent workflows.
- Knowledge/template retrieval currently supports basic text query (`q`) and exact tag filtering; semantic/vector ranking is intentionally out of scope for the current MVP.

## Frontend
- `frontend/lib/api.ts` is the thin typed client used by feature views.
- Main pages include `/dashboard`, `/today`, `/reflection`, `/technical-analysis`, `/knowledge`, `/templates`, `/orchestrate`, `/orchestrations`, and `/history`.
- `/orchestrate` supports sync/async runs, entitlement input, template operations, queue job status, and retry/cancel actions.
- `/orchestrations` supports run history filters, step replay, queue status filtering, queue job list, and timeline replay.
- The dashboard reads orchestration metrics and monetization KPI data with fallback states for unavailable observability.

## Auditability
- `AgentRunLog` records concise request/output metadata for core generation flows and monetization decisions.
- Orchestration replay is audit-oriented: each step stores input summary, output summary, structured audit JSON, fallback action, timing, and status.
- Queue replay is event-oriented: each queue status transition has a timestamped event with status and detail.
