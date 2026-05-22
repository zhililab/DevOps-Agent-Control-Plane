# MVP Demo Runbook

This runbook keeps the DevOps orchestration MVP demo short, repeatable, and focused on the current release scope.

## Demo Target

- Public app: `http://1.117.63.81`
- Health check: `http://1.117.63.81/health`
- Primary pages: `/dashboard`, `/orchestrate`, `/orchestrations`
- Release path: Docker Compose server deployment through `make release-deploy`

## Three-Minute Demo Flow

1. Open `/dashboard`.
   - Confirm orchestration KPIs, monetization indicators, and recent activity render without blocking errors.
   - Use the 7D/30D window switch to show the dashboard is reading live API state.

2. Open `/orchestrate`.
   - Click `Import Curated Templates` if curated workflow templates are not already available.
   - Pick a DevOps-focused template such as `Release Gate And Remote Deploy`, `Production Incident Triage`, or `Query Performance Optimization`.
   - Keep signed entitlement handling on the default UI path; do not use legacy `X-Subscription-Tier`.
   - Run a synchronous orchestration for the fastest demo path.

3. Review the immediate replay.
   - Confirm the result includes `Run Replay`, run id, summary, and step audit blocks.
   - Confirm each step exposes conclusion, evidence, risk, and next action.

4. Open `/orchestrations`.
   - Confirm the new run appears newest-first.
   - Confirm the run displays persisted `History Ledger: valid · N event(s)` without first clicking verify.
   - Click `Verify History Ledger` once to show manual re-verification keeps the same persisted status.

5. Review queue visibility.
   - In `Queue Job List`, filter by status if needed.
   - Select a job and confirm `Timeline Replay` shows either observed event log entries or a deterministic snapshot fallback.
   - Demonstrate retry/cancel controls only when the selected job status allows the action.

## Acceptance Checks

- `/health` returns `{"status":"ok"}`.
- `/orchestrate` and `/orchestrations` return HTTP 200.
- `/api/orchestrations/history?limit=3` includes `ledger_integrity` for returned runs.
- `/orchestrations` does not show `History Ledger: not checked` for runs that already have ledger events.
- Smoke/system records may exist from release checks, but personal history pages hide smoke data by default.

## Demo Boundaries

- This MVP demo is about deterministic DevOps orchestration, replay, auditability, and release readiness.
- Communication Assistant, Weekly Review, and third-party integrations are later product modules and should not be presented as current MVP blockers.
- k3d/k8s remains a future deployment path; the current release proof is the Docker Compose server path.
