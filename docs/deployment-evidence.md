# Deployment Evidence

This file records the current MVP deployment evidence for the Docker Compose server path.

## 2026-06-06 Dashboard API Base Fix Deployment

- Implementation commit: `426cc46 chore: release deploy 2026-06-06-1910`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- User-facing issue fixed:
  - `/dashboard` displayed `Some dashboard data is unavailable: plans, reflections, analysis.`
  - `/dashboard` also displayed `Some dashboard data is unavailable: orchestration metrics, orchestration history, commercial metrics, pilot readiness.`
  - root cause was the frontend API client defaulting to `http://localhost:8000/api` when `NEXT_PUBLIC_API_BASE` was absent; production browser requests could point at the visitor's local machine instead of the same-origin gateway
- Release fixes included:
  - frontend API client now defaults to same-origin `/api`
  - added `frontend/test/api-client.test.tsx` to assert default requests use `/api/plans/history` and never `localhost:8000`
- Release incident handled:
  - first remote deploy attempt reached commit `426cc46` but smoke failed because the server disk was full and PostgreSQL could not write `postmaster.pid`
  - remote cleanup reclaimed about `38.7GB` by pruning unused Docker images, stopped containers, and build cache; PostgreSQL data volumes were not pruned
  - server root filesystem recovered from `100%` used to about `46%` used before the successful redeploy
- Verified on local release gate:
  - `make qa-fast` passed with frontend tests: 52 tests across 15 files
  - `make qa-visual` passed: 4 tests
  - Playwright E2E passed: 3 tests
  - `make security-check` passed; npm audit still reports moderate tooling advisories below the configured high-severity release gate
  - `kubectl kustomize k8s` rendered 275 lines
  - second `make release-deploy` reran `make release-check`, found no staged changes, and deployed the already-pushed commit
- Verified on remote:
  - remote smoke checks passed for frontend routes, daily plan, reflection, technical analysis, orchestration run/history/metrics, queue run/history, monetization observability, Manual Billing lifecycle, entitlement, commercial metrics, knowledge list, and template list
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `{"status":"ok"}`
  - public `/dashboard` returned HTTP `200`
  - public `GET /api/plans/history`, `/api/reflections/history`, `/api/analysis/history`, `/api/orchestrations/metrics?days=7`, `/api/monetization/commercial-metrics?days=7`, and `/api/monetization/pilot-report?days=7` returned HTTP `200`
  - headless browser verification loaded `/dashboard` and confirmed `has-dashboard-error=false`, `has-localhost-request=false`
  - observed dashboard API requests use same-origin URLs such as `http://1.117.63.81/api/plans/history`, `http://1.117.63.81/api/orchestrations/metrics?days=7`, and `http://1.117.63.81/api/monetization/pilot-report?days=7`

## 2026-06-02 Pilot Guided Closeout V2 Deployment

- Implementation commit: `9eb7019 chore: release deploy 2026-06-02-1602`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Product value shipped:
  - Guided Pilot Closeout V2 scenario-by-scenario buyer journey on `/tutorial`
  - `GET /api/monetization/pilot-report` now includes `scenario_completion`
  - `GET /api/monetization/pilot-closeout` now includes buyer review status, next scenario, missing scenarios, and readiness summary
  - `/orchestrate?scenario=...` shows scenario guidance, expected gate behavior, required tier, approval status, success signal, and post-run CTAs
  - `missing-approval` flow explicitly supports the expected approval block first, then approval confirmation and rerun
  - `/monetization` shows Buyer Review Status and grouped Scenario Completion under Pilot Readiness
  - `/dashboard` and docs remain aligned to the commercial Pilot Closeout buyer journey
  - frontend dependency hardening pins `ws@8.20.1`; high-severity security gate remains enforced while moderate tooling advisories stay visible
- Verified on local release gate:
  - `make release-deploy` reran `make release-check`
  - frontend unit tests passed: 51 tests across 14 files
  - frontend visual baseline passed: 4 tests
  - Playwright E2E passed: 3 tests
  - backend test suite passed during `qa-fast`
  - `make security-check` passed; npm audit still reports moderate tooling advisories below the configured high-severity release gate
  - `kubectl kustomize k8s` rendered 275 lines
- Verified on remote:
  - remote smoke checks passed for frontend routes, core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, Manual Billing lifecycle, entitlement, commercial metrics, knowledge list, and template list
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `{"status":"ok"}`
  - public `/dashboard`, `/tutorial`, `/orchestrate`, `/orchestrations`, and `/monetization` returned HTTP `200`
  - public `GET /api/orchestrations/pilot-scenarios` returned the fixed five-scenario pilot pack
  - public `GET /api/monetization/pilot-report?days=7&subject=demo-user` returned `scenario_completion.total=5`, `completed=0`, `missing=5`, `next_scenario_id=high-risk-generated-pr`, and `ready_for_buyer_review=false`
  - public `GET /api/monetization/pilot-closeout?days=7&subject=demo-user` returned Markdown with `Buyer Review Status`, `Buyer review: Not ready`, and `Next scenario: High-risk generated PR`

## 2026-05-24 Pilot ROI Evidence Loop Deployment

- Implementation commit: `ec43c27 feat: add pilot ROI evidence loop`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Product value shipped:
  - ROI Aggregation V2 in `GET /api/monetization/commercial-metrics?days=7|30&subject=...`
  - Real PR/CI Adapter V1 inputs on `/orchestrate` with sanitized PR URL, diff summary, CI log summary, target environment, and change risk
  - buyer-facing `Value Generated`, review time saved, blocked risk value, and value-by-template panels on `/monetization`
  - dashboard ROI KPI cards for Estimated Value, Review Time Saved, and Blocked Risk Value
  - redacted run evidence export API and UI action: `GET /api/orchestrations/{id}/evidence` and `Export Evidence`
  - Pilot Package V1 documentation with pilot goals, demo datasets, success metrics, pricing assumptions, acceptance script, and retro template
- Verified on focused local tests:
  - `backend/.venv/bin/pytest tests/test_orchestrations.py tests/test_monetization_api.py` passed: 34 tests
  - `npm test -- --run test/monetization-flow.test.tsx test/dashboard-monetization-kpi.test.tsx test/tutorial-flow.test.tsx test/orchestration-flow.test.tsx` passed: 17 tests across 4 files
  - `git diff --check` passed
- Verified on release gates:
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed: 3 Playwright tests
  - `make security-check` passed; npm audit findings remain moderate severity and below the configured high-severity release gate
  - `make release-check` passed, including qa, visual baseline, Playwright E2E, security check, and k8s render
  - `make release-deploy` reran the full local release gate and passed
- Verified on remote:
  - remote smoke checks passed for frontend routes, core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, Manual Billing lifecycle, entitlement, and commercial metrics
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200` with `{"status":"ok"}` in about `0.070s`
  - public `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` returned HTTP `200`
  - public `GET /api/monetization/commercial-metrics?days=7` returned `roi_summary` with `runs_with_roi=76`, `estimated_customer_value_usd=6220`, `review_time_saved_minutes=1040`, and `audit_time_saved_minutes=1448`
  - public `GET /api/orchestrations/history?limit=1` returned run `#76` with ROI evidence, `ledger_integrity.status=valid`, and `checkpoint_count=7`
  - public `GET /api/orchestrations/76/evidence` returned redacted Markdown evidence export with PR/CI context, policy gate, ROI evidence, step replay, ledger status, and checkpoints
  - public `/orchestrate` HTML includes `Real PR/CI Adapter V1`
  - public `/monetization` HTML includes `Commercial Signal`, `Value Generated`, and `Value By Template`
  - public `/tutorial` HTML includes the Pilot Demo path and Pilot Dataset entries

## 2026-05-24 Release Gate ROI Evidence V1 Deployment

- Implementation commit: `60f0a0a feat: add release gate ROI evidence`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Product value shipped:
  - orchestration read/history responses now include run-level `roi_evidence`
  - `/orchestrations` audit report now shows estimated customer value, review/audit time saved, blocked risk value, billable work units, and transparent assumptions
  - `PLANS.MD` now positions the current iteration around commercial proof, ROI Evidence V1, Real PR/CI Adapter V1, and Pilot Package V1
- Verified on focused local tests:
  - `backend/.venv/bin/pytest tests/test_orchestrations.py tests/test_monetization_observability_contracts.py` passed: 24 tests
  - `npm test -- --run test/orchestration-flow.test.tsx` passed: 10 tests
  - `npm test -- --run test/tutorial-flow.test.tsx test/monetization-flow.test.tsx` passed: 5 tests
  - `git diff --check` passed
- Verified on release gates:
  - `make release-check` passed
  - `make release-deploy` reran the full local release gate and passed
  - frontend unit tests passed: 49 tests
  - frontend visual baseline passed: 4 tests
  - Playwright commercial/orchestration E2E passed: 3 tests
  - backend test suite passed during release gate: 45 tests
  - `make security-check` passed; npm audit findings remain moderate severity and below the configured high-severity release gate
  - `kubectl kustomize k8s` rendered 275 lines
- Verified on remote:
  - remote smoke checks passed for frontend routes, core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, monetization read APIs, and Manual Billing lifecycle APIs
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `{"status":"ok"}`
  - public `/orchestrations` returned HTTP `200`
  - public `GET /api/orchestrations/history?limit=1` returned `roi_evidence` with estimated customer value and transparent assumptions
  - public `GET /api/orchestrations/templates` returned `AI-generated PR Release Gate` with `required_tier=power`, `risk_level=high`, `approval_required=true`, `allowed_tool_scopes=["ci-cd-release-gate"]`, and `billable_work_units=8`

## 2026-05-23 Commercial Usage Normalization Release Verification

- Implementation commit: `e0d5ad4 fix: normalize commercial usage accounting`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- User-facing issue fixed:
  - `/monetization` showed monthly `Usage Counters` as `0 / 300` while the 7D commercial metric showed `3 / 300`
  - buyers could not tell whether the numbers represented billing-period quota or recent workflow activity
- Release fixes included:
  - successful sync orchestration runs increment billing-period `workflow_runs`
  - accepted queue runs increment billing-period `queued_runs`
  - startup backfill reconciles existing `monetization.usage_recorded` logs into current `usage_counters` without double counting
  - Manual Billing Pro/Power quota enforcement now prefers current billing-period counters
  - `GET /api/monetization/commercial-metrics` now includes `plan_usage` for the billing-period source of truth
  - `/monetization` now separates `Plan Usage` from 7D/30D `Commercial Signal`
- Verified on local gates:
  - focused backend monetization/orchestration tests passed
  - focused frontend monetization/dashboard tests passed
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed
  - `make security-check` passed; remaining npm audit findings are moderate severity and below the configured high-severity release gate
  - `make release-check` passed
- Verified on remote:
  - remote smoke checks passed, including `GET /api/monetization/commercial-metrics?days=7&subject=smoke-check` with `plan_usage`
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200` with `{"status":"ok"}` in about `0.071s`
  - public `/monetization` returned `200` in about `0.114s`
  - public `GET /api/monetization/usage?subject=demo-user` returned `workflow_runs: 3 / 300` and `queued_runs: 0 / 300`
  - public `GET /api/monetization/commercial-metrics?days=7&subject=demo-user` returned matching `plan_usage.workflow_runs_used=3`, `usage_summary.workflow_runs_used=3`, and `billable_work_units.total=9`
  - headless browser check confirmed `/monetization` renders `Plan Usage`, `Commercial Signal`, `Workflow Runs 3 / 300`, and no `Commercial Metrics V2` label

## 2026-05-23 Billing Entitlement Workflow Fix Verification

- Implementation commit: `b2d3de7 fix: connect billing entitlement to orchestration`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- User-facing issue fixed:
  - `/monetization` could show an active Pro manual subscription while `/orchestrate` still used an old/default entitlement token
  - Pro users could select a Power-only template and only discover the tier mismatch after attempting to run
- Release fixes included:
  - active Manual Billing subjects can fetch a signed orchestration token through `GET /api/monetization/entitlement?subject=...`
  - `/orchestrate` stores and reuses the same Billing Subject as `/monetization`
  - `/orchestrate` loads the subscription entitlement before falling back to the public bootstrap token
  - Power-only templates are blocked in the UI for Pro entitlement before submit, with a `Use PRO-compatible template` recovery action
  - subject-scoped Commercial Metrics V2 matches both raw billing subjects and entitlement-derived subject IDs
  - smoke coverage now includes the billing entitlement endpoint
- Verified on local gates:
  - focused backend monetization/orchestration tests passed
  - focused frontend orchestration/monetization tests passed
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed
  - `make security-check` passed; remaining npm audit findings are moderate severity and below the configured high-severity release gate
  - `make release-check` passed
- Verified on remote:
  - remote smoke checks passed, including `GET /api/monetization/entitlement?subject=smoke-check`
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200` with `{"status":"ok"}` in about `0.076s`
  - public `/orchestrate` returned `200` in about `0.133s`
  - public `/monetization` returned `200` in about `0.119s`
  - public `GET /api/monetization/entitlement?subject=demo-user` returned `200`, `tier=pro`, and a signed token
  - headless browser check loaded `demo-user` as `PRO · active`, loaded `Current entitlement: PRO` on `/orchestrate`, disabled a Power-only template for Pro, switched to a Pro-compatible template, and completed a run with `Run Replay` visible

## 2026-05-23 Commercial Metrics V2 Release Verification

- Implementation commit: `3a2075b feat: add commercial metrics v2`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release features included:
  - explicit Policy Authoring UI controls on `/orchestrate` for required tier, risk level, approval requirement, allowed tool scopes, billable work units, and enabled state
  - read-only Commercial Metrics V2 API: `GET /api/monetization/commercial-metrics?days=7|30&subject=...`
  - `/monetization` Commercial Metrics panel with 7D/30D windowing, billable work units, policy blocks, top templates, commercial events, and anomaly hints
  - dashboard Commercial Work Units and Commercial Policy Blocks cards plus line/delta/anomaly signals
  - stable pixel-level Playwright baselines for `/dashboard`, `/orchestrate`, `/orchestrations`, and `/monetization`
  - smoke coverage for the new commercial metrics API
- Verified on local gates:
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed with commercial plan flow, orchestration replay, and commercial screenshot baselines
  - `make security-check` passed; remaining npm audit findings are moderate severity and below the configured high-severity release gate
  - `make release-check` passed, including `qa-fast`, visual baseline, Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed, including `/api/monetization/commercial-metrics?days=7&subject=smoke-check`
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200` with `{"status":"ok"}` in about `0.071s`
  - public `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` returned `200`
  - public `GET /api/monetization/commercial-metrics?days=7` returned `200` in about `0.088s` with subscription summary, usage summary, commercial events, policy blocks, and billable work units

## 2026-05-22 Commercial Site Repositioning Release

- Deployed implementation commit: `2131367 feat: reposition commercial control plane site`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release additions:
  - frontend title/header repositioned to `DevOps Agent Control Plane`
  - categorized navigation for Operate, Commercial, Learn, Assets, and Personal Loops
  - animated workflow preview in the global header
  - `/monetization` renamed in UI to `Plans & Usage` with clearer Free/Pro/Power value framing
  - `/tutorial` page for commercial onboarding and demo storytelling
  - mobile navigation compressed into horizontal grouped cards so page content is visible in the first viewport
- Verified local gates:
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make release-check` passed
  - local `make smoke-check` passed with `/tutorial`
  - Playwright screenshots checked mobile `/monetization` and desktop `/tutorial`
- Verified remote deployment:
  - remote smoke checks passed, including `/tutorial`
  - remote runtime security checks passed
  - public `curl http://1.117.63.81/health` returned `200`
  - public `/dashboard` returned `200`
  - public `/monetization` returned `200`
  - public `/tutorial` returned `200`

## 2026-05-22 Manual Billing V1 Commercialization Release

- Deployed implementation commit: `78fba09 feat: add manual billing monetization flow`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release additions:
  - Manual Billing V1 lifecycle APIs:
    - `POST /api/monetization/checkout/manual`
    - `POST /api/monetization/cancel`
    - `POST /api/monetization/reactivate`
  - `/monetization` UI for plan activation, subscription status, usage counters, and billing audit events
  - smoke coverage for `/monetization` and the manual billing lifecycle APIs
- Verified local gates:
  - backend tests: 92 passed
  - frontend tests: 39 passed
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make release-check` passed
  - local `make smoke-check` passed with a signed test entitlement token
- Verified remote deployment:
  - remote smoke checks passed, including `/monetization` and manual checkout/cancel/reactivate
  - remote runtime security checks passed
  - public `curl http://1.117.63.81/health` returned `200`
  - public `/dashboard` returned `200`
  - public `/monetization` returned `200`

## 2026-05-21 Server Release

- Release path: Docker Compose server deployment through `make server-deploy`.
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- App directory on server: `/root/code/personal-agent-ws/personal-agent`
- Deployed commit: `1e005db chore: release deploy 2026-05-21-2255`
- Follow-up docs/script commit: `eb32a17 docs: align deployment health check path`
- Verified public routes:
  - `http://1.117.63.81/dashboard`
  - `http://1.117.63.81/orchestrate`
  - `http://1.117.63.81/orchestrations`

## Verification Results

- Local gate before release: `make qa-fast` passed.
- Remote deployment command completed through `make server-deploy`.
- Remote smoke checks passed for:
  - frontend routes
  - backend `/health`
  - daily plan, reflection, and technical analysis APIs
  - orchestration run, history, metrics, and queue APIs
  - monetization observability and read APIs
  - knowledge and template listing response shape
- Public post-deploy checks:
  - `curl http://1.117.63.81/health` returned `{"status":"ok"}`
  - `http://1.117.63.81/dashboard` returned `200`

## 2026-05-21 Security Hardening Baseline

- Added planned checks:
  - `make security-check`
  - gateway security headers
  - report-only CSP
  - production CORS origin configuration
  - frontend dependency high/critical audit
  - runtime entitlement, free-tier, canonical health, and oversized-payload assertions
- Expected deployment behavior:
  - remote `make server-deploy` runs smoke checks and runtime security checks
  - deployment uses `RESET_DB=0` unless the database can be discarded

## 2026-05-22 Hardening Release Verification

- Latest deployed commit: `96902f9 chore: release deploy 2026-05-22-0016`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - deterministic startup migration wrapper for legacy bootstrap-created databases
  - direct Alembic head marker recovery for existing schemas without `alembic_version`
  - forced gateway recreation during server deploy so mounted Nginx config changes take effect
  - gateway hiding of upstream `X-Powered-By`
- Verified on remote:
  - gateway and backend readiness checks passed
  - smoke checks passed for core pages and core workflow APIs
  - runtime security check passed for security headers, canonical health, entitlement boundary, oversized payload handling, and no exposed `X-Powered-By`

## 2026-05-22 History Ledger Release Verification

- Latest deployed commit: `a07e8d5 chore: release deploy 2026-05-22-0043`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - immutable `history_events` ledger table and Alembic migration
  - canonical JSON payload hashing and integrity verification service
  - orchestration, step replay, queue lifecycle, entitlement, and monetization audit event capture
  - idempotent backfill from existing orchestration, queue, step, and agent log tables
  - read-only history ledger API: `GET /api/orchestrations/{id}/history-events`
  - `/orchestrations` browser control for ledger event count and integrity status
- Verified on local gates:
  - `make qa-fast` passed
  - `make release-check` passed, including visual baseline, Playwright E2E, and security check
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - Docker Compose services were healthy after deployment
  - `curl http://1.117.63.81/health` returned `{"status":"ok"}`
  - `curl http://1.117.63.81/api/orchestrations/12/history-events` returned `integrity_status: valid` with 6 ledger events

## 2026-05-22 History Time Accuracy Release Verification

- Deployed implementation commit: `c5e5d17 fix: correct history business time storage`
- Deployed migration fix commit: `38783bc fix: commit startup migrations before upgrade`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Remote backups captured before migration rollout:
  - `deploy/backups/personal_agent-20260522-010954.sql`
  - `deploy/backups/personal_agent-20260522-011452-pre-migration-fix.sql`
- Release fixes included:
  - `APP_BUSINESS_TIMEZONE=Asia/Shanghai` business-date derivation
  - UTC-marked public datetime serialization for API responses
  - `record_source` and `business_timezone` metadata for daily plan, reflection, and technical analysis records
  - safe backfill of historical business dates from existing UTC `created_at`
  - default filtering of smoke/system records from user history, with `include_system=true` audit access
  - read-only history endpoints no longer writing `agent_run_logs`
  - Alembic startup transaction fix so PostgreSQL migrations commit before app startup
- Verified on local gates:
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed
  - `make security-check` passed
  - `make release-check` passed
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - `alembic_version` is `0011_add_business_time_metadata`
  - `daily_plans` includes `record_source` and `business_timezone`
  - default `GET /api/plans/history` returned no smoke records
  - `GET /api/plans/history?include_system=true` returned smoke records tagged `record_source=smoke_check`
  - records created after `2026-05-21T16:00:00Z` were backfilled to business date `2026-05-22`
  - `curl http://1.117.63.81/health` returned `{"status":"ok"}`
  - `http://1.117.63.81/history` returned `200`

## 2026-05-22 MVP Orchestration Closeout Baseline Verification

- Baseline deployed commit: `a3329de fix: persist orchestration ledger status`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - curated DevOps orchestration templates seeded and importable from `/orchestrate`
  - `/api/orchestrations/history` returns `ledger_integrity` summaries by default
  - `/orchestrations` displays persisted ledger status after reloads and redeploys
  - dashboard trend reads use lightweight history parameters to avoid replay/integrity overhead
- Verified on local gates:
  - `make release-check` passed, including `qa-fast`, visual baseline, Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - `curl http://1.117.63.81/health` returned `200`
  - `http://1.117.63.81/orchestrations` returned `200`
  - `GET /api/orchestrations/history?limit=3` returned persisted `ledger_integrity` summaries for the latest runs

## 2026-05-22 Policy Layer V2 And Approval Gate Verification

- Implementation commit: `30ec782 feat: add template policy approval gate`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Remote backup captured before migration rollout:
  - `deploy/backups/personal_agent-20260522-131634-pre-policy-layer-v2.sql`
- Release fixes included:
  - workflow template policy metadata for required tier, risk level, approval requirement, allowed tool scopes, and billable work units
  - template-backed sync and queued orchestration policy enforcement
  - human approval gate for approval-required templates
  - orchestration metrics fields for billable work units, successful audited workflows, approval blocks, and template policy upgrade blocks
  - `/orchestrate` template policy display and human approval confirmation control
  - dashboard KPI cards for billable work units, audited workflows, and policy blocks
- Verified on local gates:
  - focused backend policy/template/metrics tests passed
  - focused frontend orchestration/dashboard tests passed
  - empty SQLite Alembic upgrade reached `0015_refresh_workflow_template_policies`
  - `make release-check` passed, including `qa-fast`, visual baseline, Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - remote repo head was `30ec782`
  - remote `alembic_version` was `0015_refresh_workflow_template_policies`
  - `curl http://1.117.63.81/health` returned `{"status":"ok"}`
  - `GET /api/orchestrations/templates` returned `Release Gate And Remote Deploy` with `required_tier=power`, `risk_level=high`, `approval_required=true`, `allowed_tool_scopes=["server-deploy"]`, and `billable_work_units=5`
  - `GET /api/orchestrations/metrics?days=7` returned billable work unit and policy block fields
  - unapproved `Release Gate And Remote Deploy` run with a power entitlement returned `409` with `detail.code=approval_required`

## 2026-05-22 Commercial UI Polish Verification

- Implementation commit: `992205a feat: polish commercial tutorial UI`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - lighter product-shell header, softer shadows, and stronger first-screen hierarchy for `DevOps Agent Control Plane`
  - less boxy grouped navigation across Operate, Commercial, Learn, Assets, and Personal Loops
  - interactive `/tutorial` demo path for template selection, entitlement policy, replay evidence, and commercial value tracking
  - tutorial interaction regression test and generated screenshot artifacts ignored from git via `output/`
- Verified on local gates:
  - focused frontend tests passed: `app-nav`, `pages`, and `tutorial-flow`
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make release-check` passed, including Playwright E2E, security check, and k8s render
  - desktop and mobile Playwright screenshots were captured locally for `/tutorial`
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200`
  - public `/tutorial`, `/dashboard`, `/monetization`, `/orchestrate`, and `/orchestrations` returned `200`

## 2026-05-22 Commercial Monetization Robustness Release Verification

- Implementation commit: `2c42c7a fix: harden commercial monetization flow`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - `/monetization` no longer lets audit-feed or usage refresh timeouts hide a successfully activated subscription profile
  - Manual Billing V1 lifecycle responses update profile, counters, and audit feed immediately before background refresh completes
  - `/api/monetization/events` supports optional `subject` filtering so account pages do not load unrelated global audit noise
  - `/monetization` UI now emphasizes the commercial MVP cockpit: plan, usage, and audit state
  - reduced idle animation work in the global background/header preview and shortened route transition duration
  - added browser E2E for commercial plan activation alongside orchestration replay E2E
- Verified on local gates:
  - focused frontend monetization and route-transition tests passed
  - focused backend monetization API tests passed
  - `make qa-fast` passed with 45 frontend/backend tests and production build
  - `make qa-visual` passed
  - `make release-check` passed, including two Playwright E2E flows, security check, and k8s render
  - desktop and mobile Playwright screenshots were captured locally for `/monetization`
- Verified on remote:
  - first deploy attempt failed on a transient Docker registry TLS handshake timeout for `node:20-alpine`; retry succeeded without database reset
  - remote smoke checks passed
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health`, `/monetization`, `/dashboard`, `/orchestrate`, and `/orchestrations` returned `200`
  - public `POST /api/monetization/checkout/manual` activated a Pro test account
  - public `GET /api/monetization/events?subject=...&limit=3` returned the account-scoped `checkout_completed` event

## 2026-05-22 Team Trust Layer V1 Release Verification

- Implementation commit: `e5d0655 feat: add team trust checkpoint layer`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release features included:
  - State & Checkpoint V2 persistence for orchestration, step, and queue lifecycle state snapshots
  - canonical JSON + SHA-256 checkpoint payload integrity checks with existing sensitive-field redaction rules
  - lightweight team trust metadata on orchestration and queue runs: `team_subject`, `requested_by`, `approval_actor`, and `approval_note`
  - checkpoint history API: `GET /api/orchestrations/{id}/checkpoints`
  - team-filtered orchestration and queue history
  - `/orchestrate` team/requester/approver inputs for commercial demos
  - `/orchestrations` checkpoint timeline, actor summary, team filter, and persistent ledger verification display
  - dashboard Team Trust KPIs for approved runs, checkpointed runs, policy blocks, and failed jobs needing owner
  - tutorial demo path updated to Run -> Approve -> Checkpoint -> Replay -> Verify -> Upgrade
- Verified on local gates:
  - full backend test suite passed
  - full frontend test suite passed
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed with ledger verification persistence and checkpoint timeline checks
  - `make security-check` passed; remaining npm audit findings are below the configured high-severity gate and require future breaking upgrades
  - `make release-check` passed, including Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200` with `{"status":"ok"}`
  - public `/dashboard`, `/orchestrate`, `/orchestrations`, and `/monetization` returned `200`
  - public `GET /api/orchestrations/history?limit=1` returned a run with team metadata, `ledger_integrity.integrity_status=valid`, and `checkpoint_count=7`
  - public `GET /api/orchestrations/49/checkpoints` returned seven valid checkpoint events: `queue.queued`, `queue.started`, `orchestration.accepted`, `step.started`, `step.success`, `orchestration.success`, and `queue.succeeded`

## 2026-05-22 Orchestration Loading Robustness And Gateway Performance Verification

- Implementation commits:
  - `949e303 fix: harden orchestration request loading`
  - `ec93cd6 perf: reduce navigation prefetch load`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - raised frontend API timeout budgets for orchestration, queue, checkpoint, entitlement, and workflow template calls
  - added retry handling for transient browser-side GET aborts/network failures without retrying mutating POST calls
  - reduced `/orchestrations` first-load history and queue list limits from 50 to 25
  - extended frontend tests to cover transient abort recovery for workflow template loading and orchestration/queue history loading
  - extended Playwright E2E to assert no `Request timed out. Please retry.` state on `/orchestrate` and `/orchestrations`
  - kept queue history as a lightweight summary response without eager event/checkpoint payloads
  - disabled global navigation prefetch to prevent first-load route chunk/RSC fan-out on slow public links
  - enabled Nginx gzip for JavaScript, JSON, CSS, SVG, XML, and text responses
- Verified on local gates:
  - full backend test suite passed
  - full frontend test suite passed with 47 tests
  - frontend production build passed
  - `make qa-fast` passed
  - `make qa-visual` passed
  - `make e2e-orchestration` passed
  - `make security-check` passed, including the static gzip config assertion
  - `make release-check` passed, including Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200`
  - public `GET /api/orchestrations/templates` returned `200` in under one second during verification
  - public `GET /api/orchestrations/queue/history?limit=3` returned `200` in under one second during verification
  - public JS chunk responses returned `Content-Encoding: gzip` when requested with `Accept-Encoding: gzip`
  - real browser verification for `/orchestrate` showed `orchestrateTimeouts=0`, workflow templates present, and `rscPrefetchAfterOrchestrate=0`
  - real browser verification for `/orchestrations` showed history and queue loading states cleared with no `Request timed out. Please retry.`

## 2026-05-30 Pilot Closeout Conversion Release Verification

- Implementation commits:
  - `6d69dc9 feat: add pilot conversion readiness loop`
  - `51a8270 feat: add pilot closeout conversion report`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release features included:
  - `pilot_scenario_id` stored on orchestration run requests and surfaced on run reads/evidence bundles
  - `GET /api/monetization/pilot-closeout?days=7|30&subject=...&team_subject=...`
  - scenario completion tracking for the five static pilot scenarios
  - `/monetization` `Why Power` upgrade evidence from policy, approval, evidence, ledger, checkpoint, and ROI data
  - `/monetization` copy/download actions for the buyer-facing Pilot Closeout Markdown report
  - `/tutorial` pilot progress indicator for scenario completion
  - docs alignment across `PLANS.MD`, `PLANS.html`, `AGENTS.md`, `README.md`, core check, demo runbook, and pilot package
- Verified on local gates:
  - focused backend tests passed: `tests/test_orchestrations.py`, `tests/test_monetization_api.py`, `tests/test_orchestration_query_performance.py`
  - focused frontend tests passed: monetization flow, tutorial flow, orchestration flow, and dashboard monetization KPI tests
  - frontend production build passed
  - `make qa-fast` passed with 50 frontend tests plus backend suite and production build
  - `make qa-visual` passed
  - `make e2e-orchestration` passed with 3 Chromium flows
  - `make security-check` passed; npm audit still reports moderate tooling warnings below the configured high-severity gate
  - `make release-check` passed, including Playwright E2E, security check, and k8s render
- Verified on remote:
  - remote smoke checks passed
  - remote runtime security checks passed
  - public `GET http://1.117.63.81/health` returned `200`
  - public `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` returned `200`
  - public `GET /api/orchestrations/pilot-scenarios` returned all five pilot scenarios
  - public `GET /api/monetization/pilot-report?days=7&subject=demo-user` returned `scenario_statuses` and `power_upgrade_evidence`
  - public `GET /api/monetization/pilot-closeout?days=7&subject=demo-user` returned redaction-safe Markdown with `Pilot Closeout Report`, `Scenario Completion`, `Why Power`, and `Next Buyer Action`
  - public `GET /api/monetization/commercial-metrics?days=7&subject=demo-user` returned `plan_usage`, `usage_summary`, `roi_summary`, `top_templates`, and `trend`

## 2026-07-16 Agent Quality Lab Production Evidence

- Implementation commits:
  - `75ac255 feat: add real provider quality evidence`
  - `28b1ad9 fix: isolate provider credentials from release tests`
  - `434acd8 fix: renew expired manual subscriptions`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Database reset: `RESET_DB=0`
- Remote PostgreSQL backup before migration:
  - `/root/code/personal-agent-ws/personal-agent/backups/personal_agent_pre_0018_20260715_234932.sql.gz`
  - verified non-empty size: `240K`
- Remote migration: `0018_add_llm_evaluation_feedback`
- Release behavior:
  - added Agent Quality Lab persistence, fixed evaluation dataset, feedback, and Pilot measurements
  - kept deterministic release policy authoritative and real-provider observations explicit opt-in
  - protected production evaluation mutations with independent `X-Evaluation-Access`
  - prevented release/E2E subprocesses from consuming production Provider quota
  - renewed expired Manual Billing periods without deleting historical usage or audit data
- Local release verification:
  - full `make release-check` passed, including backend tests, 56 frontend tests, production build, visual tests, four Playwright flows, security checks, npm audit with zero vulnerabilities, and k8s render
- Remote release verification:
  - remote head was `434acd8`
  - backend, frontend, gateway, and PostgreSQL containers were running
  - public `/health`, `/dashboard`, `/evaluation`, `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` returned `200`
  - Provider status reported enabled/configured, model `doubao-seed-2.0-code`, prompt `pr-ci-gate.v1`, and write protection without returning credentials
  - anonymous `POST /api/evaluations/runs` returned `401`
  - production runtime `scripts/security_check.sh` passed
  - remote smoke checks passed after the expired-subscription renewal regression was fixed
- Production real-provider evaluation:
  - run `#1`, dataset `pr-ci-gate.v1.25`, status `completed`
  - `25 / 25` Provider calls succeeded and `25 / 25` expected decisions matched
  - accuracy `100%`, false positives `0`, false negatives `0`
  - input tokens `5,844`, output tokens `5,703`, average latency `8,527ms`
  - marginal token cost reported `$0.00` under the subscription-backed zero-token-price configuration; subscription purchase cost is not represented as zero
  - the initial synchronous HTTP request returned Nginx `504` after the gateway timeout, but the persisted backend run continued to completion; no duplicate evaluation was submitted
- Production Pilot observation:
  - subject `quality-evidence`, team `platform-team`
  - `release_lead_time_minutes`, Pilot value `0.1421`, sample size `25`
  - human Baseline remains absent, so `improvement_rate` is `null` and estimated ROI remains separate

## Operational Notes

- The current release path is the Docker Compose server path, not k3d/k8s.
- k3d/k8s manifests remain useful for follow-up deployment validation.
- `REMOTE_RESET_DB=1` must only be used when the remote database can be discarded.
- Routine docs/script updates should sync the repository without running a destructive reset deployment.
