# MVP Demo Runbook

This runbook keeps the DevOps orchestration MVP demo short, repeatable, and focused on the current release scope.

## Demo Target

- Public app: `http://1.117.63.81`
- Health check: `http://1.117.63.81/health`
- Primary pages: `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, `/tutorial`
- Release path: Docker Compose server deployment through `make release-deploy`

## Three-Minute Demo Flow

1. Open `/dashboard`.
   - Confirm orchestration KPIs, monetization indicators, and recent activity render without blocking errors.
   - Use the 7D/30D window switch to show the dashboard is reading live API state.

2. Open `/orchestrate`.
   - Click `Import Curated Templates` if curated workflow templates are not already available.
   - Pick a DevOps-focused template such as `Release Gate And Remote Deploy`, `Production Incident Triage`, or `Query Performance Optimization`.
   - Confirm Team, Requester, Approver, and Approval Note are populated for the small-team trust demo.
   - Point out the selected template pattern and policy line: required tier, risk level, approval status, billable work units, and allowed tool scope.
   - If creating a new template, use the Policy Authoring controls instead of editing policy tags directly.
   - For high-risk templates, tick `Human Approval Confirmed` before running; the backend rejects unapproved high-risk runs.
   - Keep signed entitlement handling on the default UI path; do not use legacy `X-Subscription-Tier`.
   - Run a synchronous orchestration for the fastest demo path.

3. Review the immediate replay.
   - Confirm the result includes `Run Replay`, run id, summary, and step audit blocks.
   - Confirm each step exposes conclusion, evidence, risk, and next action.
   - Confirm the replay summary shows team/requester/approver context and a non-zero checkpoint count.

4. Open `/orchestrations`.
   - Confirm the new run appears newest-first.
   - Confirm the run displays persisted `History Ledger: valid · N event(s)` without first clicking verify.
   - Click `Verify History Ledger` once to show manual re-verification keeps the same persisted status and loads checkpoint timeline snapshots.
   - Reload the page and confirm the ledger status and checkpoint count remain visible.

5. Review queue visibility.
   - In `Queue Job List`, filter by status if needed.
   - Select a job and confirm `Timeline Replay` shows either observed event log entries or a deterministic snapshot fallback.
   - Demonstrate retry/cancel controls only when the selected job status allows the action.

6. Open `/monetization`.
   - Show the `Commercial MVP` cockpit: plan state, usage counters, and `Commercial Audit Feed`.
   - Show `Commercial Metrics V2`: billable work units, policy blocks, top value templates, lifecycle events, and the 7D/30D window switch.
   - Activate or refresh a Pro/Power plan for a demo account and confirm the audit feed is scoped to that account.
   - Explain that Manual Billing V1 is the current demoable commercial loop before real payment-provider integration.

7. Open `/tutorial`.
   - Use the run -> replay -> verify -> upgrade path as the short buyer story.

8. Close with commercial KPIs on `/dashboard`.
   - Show `Billable Work Units`, `Audited Workflows`, `Policy Blocks`, `Approved Runs`, `Checkpointed Runs`, and `Jobs Needing Owner`.
   - Explain that these counters are the current bridge from technical workflow execution to pricing and packaging.

## Acceptance Checks

- `/health` returns `{"status":"ok"}`.
- `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` return HTTP 200.
- `/api/orchestrations/history?limit=3` includes `ledger_integrity` for returned runs.
- `/api/orchestrations/{id}/checkpoints` returns checkpoint snapshots with valid payload hash status.
- `/api/orchestrations/metrics?days=7` includes billable work units, audited workflow count, approval blocks, template policy upgrade blocks, approved runs, checkpointed runs, and failed jobs needing owner.
- `/api/monetization/commercial-metrics?days=7` includes subscription summary, usage summary, policy blocks, billable work units, top templates, commercial events, trend, and anomaly hints.
- `/orchestrations` does not show `History Ledger: not checked` for runs that already have ledger events.
- `/orchestrations` shows team/requester/approver context and checkpoint count for the new run.
- `/monetization` can activate a Pro plan and show usage counters plus `checkout completed` in the audit feed without timeout errors.
- `/orchestrate` can save a template with explicit commercial policy controls: tier, risk, approval, tool scopes, work units, and enabled state.
- Smoke/system records may exist from release checks, but personal history pages hide smoke data by default.

## Demo Boundaries

- This MVP demo is about deterministic DevOps orchestration, replay, auditability, and release readiness.
- Communication Assistant, Weekly Review, and third-party integrations are later product modules and should not be presented as current MVP blockers.
- k3d/k8s remains a future deployment path; the current release proof is the Docker Compose server path.
