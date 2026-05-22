# Agent Orchestration Commercial Strategy

Last reviewed: 2026-05-22.

## Positioning

The current MVP should be positioned as a **Personal DevOps Agent Control Plane**: a deterministic, replayable, policy-gated orchestration surface for DevOps/SRE workflows. It is not a generic chatbot and not yet a broad personal operating system release. The commercial wedge is narrower and sharper:

- turn operational context into auditable Planner -> Analyzer -> Reviewer runs
- preserve step replay, queue lifecycle, ledger integrity, and entitlement evidence
- package reusable workflow templates around release, incident, security, history, and deployment work
- make every generated result inspectable enough for solo operators and small teams to trust

This matches the current technical asset base: deterministic orchestration, queue controls, signed entitlement, immutable history ledger, smoke/security/release gates, and Docker Compose deployment evidence.

## Market Signals

The market is rewarding agent products that move from answers to governed work execution:

- Salesforce reported Agentforce ARR of $800M in FY26 Q4, alongside Agentforce/Data 360 ARR above $2.9B and 29,000 Agentforce deals. Source: https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Fourth-Quarter-Fiscal-2026-Results/default.aspx
- Glean announced $100M ARR in February 2025 and later reported surpassing $200M ARR in May 2026, with agent orchestration, enterprise permissions, connectors, and governance as visible product themes. Sources: https://www.glean.com/press/glean-achieves-100m-arr-in-three-years-delivering-true-ai-roi-to-the-enterprise and https://www.glean.com/blog/glean-200m-arr-milestone
- UiPath remains a useful automation-market reference because it monetizes governed workflow execution and reports ARR as a core operating metric. Source: https://www.nasdaq.com/press-release/uipath-reports-fourth-quarter-and-full-year-fiscal-2026-financial-results-2026-03-11

The lesson for this product is not to copy CRM, enterprise search, or RPA. The lesson is that buyers pay for trusted execution surfaces: workflow ownership, observability, permissions, repeatability, and measurable work units.

## Pattern Registry

The current implementation uses `pattern:*` workflow template tags as the first pattern registry. This keeps the data model stable while making orchestration intent explicit in APIs, migrations, and UI.

| Pattern | Current Meaning | MVP Use |
| --- | --- | --- |
| `pattern:sequential` | Deterministic pipeline where each step builds on previous context. | Default Planner -> Analyzer -> Reviewer runs. |
| `pattern:maker-checker` | One agent produces work, another validates evidence/risk before acceptance. | Security, ledger, history accuracy, visual QA. |
| `pattern:handoff` | A workflow prepares evidence for a separate operational owner or environment. | Kubernetes/k3d path readiness. |
| `pattern:concurrent` | Multiple agents independently analyze the same task before aggregation. | Future engine capability, not enabled in current runner. |
| `pattern:magentic-ready` | Autonomous adaptive orchestration with external tool use and stronger governance. | Future roadmap only. |

The technical references reinforce starting simple and only adding coordination complexity when the task requires it:

- Microsoft AI agent orchestration patterns: https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns
- The Orchestration of Multi-Agent Systems: https://arxiv.org/html/2601.13671v1
- Multi-Agent Orchestration chapter: https://gerred.github.io/building-an-agentic-system/second-edition/part-iv-advanced-patterns/chapter-10-multi-agent-orchestration.html

## Commercial Value Map

| Customer Pain | MVP Capability | Value Proof |
| --- | --- | --- |
| AI outputs are hard to trust. | Step replay, audit blocks, history ledger verification. | Users can inspect conclusion, evidence, risk, and next action. |
| DevOps work needs repeatable gates. | Release/security/smoke templates and `make release-check`. | Same workflow can be rerun before each deploy. |
| Async work disappears after submit. | Queue list, status timeline, retry/cancel controls. | Operators can see lifecycle and recover failed jobs. |
| Pricing needs a usage boundary. | Signed entitlement and free/pro/power gates. | Capability limits can be enforced without plain tier headers. |
| Teams need proof after deployment. | Deployment evidence docs, smoke/security checks, public health checks. | Release status is documented and reproducible. |

## Requirement Priorities

### Implemented Now

- deterministic sequential orchestration
- reusable workflow templates
- signed entitlement gate
- async queue lifecycle
- immutable history ledger and integrity API
- security/release/smoke gates
- Docker Compose server deployment path
- pattern registry via `pattern:*` template tags
- Policy Layer V2 via template policy metadata for required tier, risk level, approval requirement, allowed tool scopes, and billable work units
- Human Approval Gate for approval-required templates before sync or queued execution
- commercial work-unit counters in orchestration metrics and dashboard KPIs
- Manual Billing V1 subscription lifecycle: manual checkout, tier changes, cancellation/reactivation, usage counters, audit feed, and `/monetization` UI

### Next High-Value Requirements

- State & Checkpoint V2: resumable queue jobs and explicit checkpoint snapshots per step.
- Agent Communication Contract: standardized inter-step message schema beyond current audit block.
- Tool Isolation: scoped credentials and deny-by-default external tool execution.
- Policy Authoring UI: first-class controls for editing template policy without typing tags.
- Commercial Metrics V2: real billing-provider integration and cohort reporting around billable work units.

## Packaging Direction

- Free: single-step smoke and personal experimentation.
- Pro: deterministic multi-step DevOps workflows, history, replay, queue controls, and local/server deployment.
- Power: policy packs, approval gates, advanced ledger/compliance evidence, team-ready observability, and higher limits.

Manual Billing V1 intentionally uses the existing tables instead of a live payment provider. It makes the commercial loop demoable and testable now, while keeping Stripe or another provider as a later adapter behind the same subscription/profile/usage/event model.

The MVP should keep selling trust and repeatability before breadth. Communication Assistant, Weekly Review, and broad integrations remain valuable later modules, but they should not displace the current DevOps orchestration control-plane wedge.
