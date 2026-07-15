# Agent Quality Evidence

This file separates implemented evaluation capability from measured provider evidence.

## 2026-07-15 Local Pre-release Provider Evaluation

- Dataset: `pr-ci-gate.v1.25`
- Provider: Volcengine Ark Coding Plan
- Model: `doubao-seed-2.0-code`
- Prompt version: `pr-ci-gate.v1`
- Run status: `completed`
- Cases: `25`
- Matching decisions: `24`
- Accuracy: `96%`
- Unsafe approvals / false negatives: `0`
- Approve cases unnecessarily gated / false positives: `0`
- Input tokens: `5,844`
- Output tokens: `5,759`
- Average provider latency: `5,875ms` per case
- Estimated marginal API cost: `$0.00` because the run used a subscription plan with token prices configured as zero; this does not treat the subscription purchase price as zero.

The single mismatch was `ci-failed-review`: the fixed label expected `needs human review`, while the model returned `block`. This is a conservative over-blocking decision, not an unsafe approval.

## 2026-07-16 Production Provider Evaluation

- Deployment commit: `434acd8 fix: renew expired manual subscriptions`
- Dataset: `pr-ci-gate.v1.25`
- Provider: Volcengine Ark Coding Plan
- Model: `doubao-seed-2.0-code`
- Prompt version: `pr-ci-gate.v1`
- Run: `#1`, status `completed`
- Cases / successful provider calls: `25 / 25`
- Matching decisions: `25`
- Accuracy: `100%`
- Unsafe approvals / false negatives: `0`
- Approve cases unnecessarily gated / false positives: `0`
- Input tokens: `5,844`
- Output tokens: `5,703`
- Average provider latency: `8,527ms` per case
- Estimated marginal API cost: `$0.00` because the subscription-backed provider has token prices configured as zero. This does not claim that the subscription itself is free.

The initial synchronous request crossed the Nginx response timeout and returned `504` to the caller, while the backend continued the same persisted run to completion. No duplicate run was submitted. Long live evaluations should move to an asynchronous submit-and-poll contract before this surface is used by multiple operators.

## Production Measured Pilot Observation

- Metric: release-gate model decision latency
- Phase: Pilot
- Value: `0.1421 minutes` per case
- Sample size: `25`
- Source: production run `#1`, `observed-live-evaluation`

No human-review Baseline has been recorded yet. Until a reviewer completes a timed baseline, this observation must not be presented as review time saved or audited ROI improvement.

## Security Evidence

- The screenshot-exposed key was disabled.
- The replacement key is environment-only and is excluded from Git.
- Provider status and invocation APIs expose provider/model/prompt/token/latency/cost metadata without returning the credential.
- Evaluation runs, feedback, and Pilot observations require a separate production write-access secret; the browser never receives the provider API key.
- Ordinary orchestration model observations are explicit opt-in, preventing silent provider-quota consumption.
- The deterministic release gate remains authoritative when the provider fails or disagrees.
