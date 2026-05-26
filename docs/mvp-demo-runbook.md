# MVP Demo Runbook

This runbook keeps the DevOps orchestration MVP demo short, repeatable, and focused on the current release scope: AI-generated PR -> release gate -> human approval -> execute or block -> ledger/checkpoint/ROI evidence.

## Demo Target

- Public app: `http://1.117.63.81`
- Health check: `http://1.117.63.81/health`
- Primary pages: `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, `/tutorial`
- Release path: Docker Compose server deployment through `make release-deploy`

## Scenario-Driven Demo Flow

1. Open `/monetization`.
   - Activate or refresh a Power plan for `demo-user`.
   - Confirm `Plan Usage`, `Commercial Signal`, and `Commercial Audit Feed` render independently.

2. Open `/tutorial`.
   - Introduce the pilot path: Import PR context -> Run Gate -> Verify Evidence -> See ROI -> Compare Plan.
   - Choose a Pilot Dataset card: high-risk generated PR, low-risk docs PR, CI flaky release, missing approval, or rollback-sensitive release.
   - Confirm the link opens `/orchestrate?scenario=<id>`.

3. Open `/orchestrate?scenario=<id>`.
   - Confirm `Pilot Scenario Pack V2` has loaded the selected scenario.
   - Load the demo account entitlement from `Billing Subject`; Power should run the release-gate scenario.
   - Confirm the PR evidence inputs are populated: PR URL, PR diff summary, CI logs, change risk, and deployment environment.
   - Confirm Team, Requester, Approver, and Approval Note are populated for the small-team trust demo.
   - Point out the selected template pattern and policy line: required tier, risk level, approval status, billable work units, and allowed tool scope.
   - If creating a new template, use the Policy Authoring controls instead of editing policy tags directly.
   - For high-risk templates, tick `Human Approval Confirmed` before running; the backend rejects unapproved high-risk runs.
   - For the missing-approval scenario, first demonstrate the `409` block, then confirm approval and rerun.
   - Keep signed entitlement handling on the default UI path; do not use legacy `X-Subscription-Tier`.
   - Run a synchronous orchestration for the fastest demo path.

4. Review the immediate replay.
   - Confirm the result includes `Run Replay`, run id, summary, and step audit blocks.
   - Confirm the release gate decision is one of `approve`, `block`, or `needs human review`.
   - Confirm each step exposes conclusion, evidence, risk, and next action.
   - Confirm the replay summary shows team/requester/approver context and a non-zero checkpoint count.

5. Open `/orchestrations`.
   - Confirm the new run appears newest-first.
   - Confirm the run reads as an audit report: requester/approver, policy gate, queue timeline, step evidence, checkpoint hash, billable work units, and blocked risk.
   - Confirm `ROI Evidence` shows estimated customer value, review/audit time saved, blocked risk value, work units, and the first transparent assumption.
   - Click `Export Evidence` and confirm the redacted Markdown bundle includes PR/CI context, approval, policy gate, step replay, ledger/checkpoint status, and ROI assumptions.
   - Use `Copy Markdown` or `Download Markdown`; the download name must be `orchestration-<id>-evidence.md`.
   - Confirm the run displays persisted `History Ledger: valid · N event(s)` without first clicking verify.
   - Click `Verify History Ledger` once to show manual re-verification keeps the same persisted status and loads checkpoint timeline snapshots.
   - Reload the page and confirm the ledger status and checkpoint count remain visible.

6. Review queue visibility.
   - In `Queue Job List`, filter by status if needed.
   - Select a job and confirm `Timeline Replay` shows either observed event log entries or a deterministic snapshot fallback.
   - Demonstrate retry/cancel controls only when the selected job status allows the action.

7. Open `/monetization`.
   - Show the `Commercial MVP` cockpit: plan state, `Plan Usage`, and `Commercial Audit Feed`.
   - Show `Commercial Signal`: Value Generated, review time saved, blocked risk value, billable work units, 7D/30D activity, policy blocks, top value templates, lifecycle events, and the window switch.
   - Show `Pilot Readiness`: completed runs, evidence-exportable runs, ledger-valid runs, checkpointed runs, metadata completeness, estimated pilot value, and recommended next action.
   - Activate or refresh a Pro/Power plan for a demo account and confirm the audit feed is scoped to that account.
   - Explain that Manual Billing V1 is the current demoable commercial loop before real payment-provider integration.

8. Close with commercial KPIs on `/dashboard`.
   - Show `Billable Work Units`, `Audited Workflows`, `Policy Blocks`, `Approved Runs`, `Checkpointed Runs`, and `Jobs Needing Owner`.
   - Show `Pilot Ready`, `Estimated Value`, `Review Time Saved`, and `Blocked Risk Value`.
   - Explain that these counters are the current bridge from governed agent execution to pricing, packaging, and ROI.

## Acceptance Checks

- `/health` returns `{"status":"ok"}`.
- `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` return HTTP 200.
- `/api/orchestrations/history?limit=3` includes `ledger_integrity` for returned runs.
- `/api/orchestrations/{id}/checkpoints` returns checkpoint snapshots with valid payload hash status.
- `/api/orchestrations/metrics?days=7` includes billable work units, audited workflow count, approval blocks, template policy upgrade blocks, approved runs, checkpointed runs, and failed jobs needing owner.
- `/api/monetization/commercial-metrics?days=7` includes subscription summary, usage summary, policy blocks, billable work units, top templates, commercial events, trend, and anomaly hints.
- `/api/monetization/commercial-metrics?days=7` includes ROI summary with estimated customer value, review/audit time saved, blocked risk value, and work units by template.
- `/api/orchestrations/pilot-scenarios` returns five static scenario records with release-gate, daily, technical, reflection, expected behavior, tier, approval, and success-signal fields.
- `/api/monetization/pilot-report?days=7&subject=demo-user` returns Pilot Readiness with evidence/ledger/checkpoint/ROI counts and no sensitive strings.
- `/api/orchestrations/{id}/evidence` returns a redacted Markdown evidence export for a run.
- `/api/monetization/entitlement?subject=demo-user` issues a signed token for an active Manual Billing subscription.
- `/orchestrations` does not show `History Ledger: not checked` for runs that already have ledger events.
- `/orchestrations` shows team/requester/approver context and checkpoint count for the new run.
- `/monetization` can activate a Pro plan and show usage counters plus `checkout completed` in the audit feed without timeout errors.
- `/orchestrate` can save a template with explicit commercial policy controls: tier, risk, approval, tool scopes, work units, and enabled state.
- `/orchestrate` blocks a Pro entitlement before submitting a Power-only template and offers a Pro-compatible template path.
- `/orchestrate` can run `AI-generated PR Release Gate` with Power entitlement and human approval, producing decision/evidence/risk/next action output.
- `/orchestrations` shows requester/approver, policy gate, queue timeline, checkpoint hash, billable work units, blocked risk, and ROI Evidence for the release-gate run.
- Smoke/system records may exist from release checks, but personal history pages hide smoke data by default.

## Demo Boundaries

- This MVP demo is about deterministic DevOps orchestration, replay, auditability, and release readiness.
- Communication Assistant, Weekly Review, and third-party integrations are later product modules and should not be presented as current MVP blockers.
- k3d/k8s remains a future deployment path; the current release proof is the Docker Compose server path.
