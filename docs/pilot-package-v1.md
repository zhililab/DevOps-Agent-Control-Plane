# Pilot Package V1

This package turns the DevOps Agent Control Plane into a repeatable enterprise trial around one buyer workflow:
AI-generated PR -> release gate -> human approval -> execute/block -> ledger/checkpoint/evidence export -> ROI signal.

## Pilot Conversion V2 Additions

- Static scenario API: `GET /api/orchestrations/pilot-scenarios`.
- Pilot readiness API: `GET /api/monetization/pilot-report?days=7|30&subject=...&team_subject=...`.
- Scenario-driven UI: `/tutorial` links to `/orchestrate?scenario=<id>`, and `/orchestrate` can load the scenario into PR/CI adapter, planner, analyzer, reviewer, approval, and template fields.
- Evidence closeout: `/orchestrations` supports `Copy Markdown` and `Download Markdown` for each exported bundle.
- Buyer KPI closeout: `/monetization` shows `Pilot Readiness`; `/dashboard` shows `Pilot Ready`.

## Pilot Goal

- Validate that governed agent execution can reduce release-review time without removing human ownership.
- Prove that risky AI-generated PRs can be blocked or escalated with replayable evidence.
- Produce a buyer-readable evidence bundle for each governed run.
- Connect release-gate activity to estimated customer value, not only internal usage.

## Required Inputs

- PR URL or stable PR identifier.
- Sanitized PR diff summary.
- Sanitized CI log summary.
- Target deployment environment.
- Change risk statement.
- Requester, approver, team, and approval note.

Do not paste raw credentials, tokens, secrets, passwords, or private customer data.

## Demo Dataset

| Scenario ID | Scenario | Expected Gate Behavior | Success Signal |
| --- | --- | --- | --- |
| `high-risk-generated-pr` | High-risk generated PR | Needs human review | Power-gated release evidence with human approval and ROI. |
| `low-risk-docs-pr` | Low-risk docs PR | Approve | Evidence export shows low-risk context and fast review path. |
| `ci-flaky-release` | CI flaky release | Needs human review | Checkpointed retry evidence supports owner assignment. |
| `missing-approval` | Missing approval | Block before execution | Policy gate returns `409` until approval is confirmed. |
| `rollback-sensitive-release` | Rollback-sensitive release | Block | Evidence export records rollback-sensitive blocked risk value. |

## Trial Success Metrics

- At least 5 release-gate runs completed with evidence export.
- At least 5 runs have valid ledger events.
- At least 5 runs have checkpoint snapshots.
- At least 1 risky PR is blocked or escalated before execution.
- At least 80% of runs include team, requester, approver, approval note, policy gate, ledger, checkpoint, and ROI evidence.
- Buyer can explain estimated value from Commercial Signal without reading raw agent output.
- No evidence export includes raw entitlement, token, password, secret, or API key text.

## Pricing Assumptions

- Free: evaluation only, single-step smoke workflows.
- Pro: daily multi-step DevOps workflows for operating teams.
- Power: approval gates, release-risk evidence, audit bundles, and higher limits.

Manual Billing V1 remains the trial billing model. Stripe or another payment provider should be added after the buyer accepts the ROI and evidence model.

## Proof Script

1. Open `/monetization`, activate or refresh Power for `demo-user`.
2. Open `/tutorial`, choose a Pilot Dataset card.
3. Confirm `/orchestrate?scenario=<id>` loaded the PR/CI adapter packet, team metadata, approval state, and recommended template.
4. Run the gate with signed Power entitlement. For `missing-approval`, first show the `409` block, then confirm approval and rerun.
5. Open `/orchestrations`, verify ledger/checkpoints, export evidence, then copy or download Markdown.
6. Open `/monetization`, show Plan Usage, Commercial Signal value, and Pilot Readiness.
7. Open `/dashboard`, show Pilot Ready, Estimated Value, Review Time Saved, and Blocked Risk Value.

## Buyer Retro Template

- Which scenario best matched your real release-risk problem?
- Did the evidence bundle contain enough context for release review or incident audit?
- Which policy boundary mattered most: tier, approval, tool scope, or blocked risk?
- Which ROI estimate was credible enough to keep: review time saved, audit time saved, or blocked risk value?
- What extra field is needed before a paid pilot: owner, service, environment, compliance tag, or rollback evidence?
- Should the next pilot step be more scenarios, a real PR/CI adapter, or a payment-provider integration?
