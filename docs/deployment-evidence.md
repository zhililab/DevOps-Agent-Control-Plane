# Deployment Evidence

This file records the current MVP deployment evidence for the Docker Compose server path.

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

## Operational Notes

- The current release path is the Docker Compose server path, not k3d/k8s.
- k3d/k8s manifests remain useful for follow-up deployment validation.
- `REMOTE_RESET_DB=1` must only be used when the remote database can be discarded.
- Routine docs/script updates should sync the repository without running a destructive reset deployment.
