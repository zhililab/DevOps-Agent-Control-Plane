# Pilot Package V1

This package turns the DevOps Agent Control Plane into a repeatable enterprise trial around one buyer workflow:
AI-generated PR -> release gate -> human approval -> execute/block -> ledger/checkpoint/evidence export -> ROI signal.

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

| Scenario | Expected Gate Behavior | Success Signal |
| --- | --- | --- |
| High-risk generated PR | Needs human review or block | ROI evidence shows blocked risk value. |
| Low-risk docs PR | Approve | Evidence export shows low-risk context and fast review path. |
| CI flaky release | Needs human review | Analyzer cites CI instability and next validation action. |
| Missing approval | Block before execution | Policy gate rejects unapproved high-risk run. |
| Rollback-sensitive rollout | Needs human review or block | Evidence export includes rollback-sensitive risk. |

## Trial Success Metrics

- At least 5 release-gate runs completed with evidence export.
- At least 1 risky PR blocked or escalated before execution.
- At least 80% of runs include requester, approver, policy gate, ledger, checkpoint, and ROI evidence.
- Buyer can explain estimated value from Commercial Signal without reading raw agent output.
- No evidence export includes raw entitlement, token, password, secret, or API key text.

## Pricing Assumptions

- Free: evaluation only, single-step smoke workflows.
- Pro: daily multi-step DevOps workflows for operating teams.
- Power: approval gates, release-risk evidence, audit bundles, and higher limits.

Manual Billing V1 remains the trial billing model. Stripe or another payment provider should be added after the buyer accepts the ROI and evidence model.

## Proof Script

1. Open `/tutorial` and introduce the pilot path.
2. Open `/orchestrate`, load a Power entitlement, and select `AI-generated PR Release Gate`.
3. Fill the Real PR/CI Adapter V1 packet or use the built-in demo defaults.
4. Confirm human approval and run the gate.
5. Open `/orchestrations`, verify ledger/checkpoints, and export evidence.
6. Open `/monetization`, show Plan Usage and Commercial Signal value.
7. Open `/dashboard`, show Estimated Value, Review Time Saved, and Blocked Risk Value.
