# AGENTS.md

## Project Purpose
Build a DevOps Agent Control Plane that lets small teams run AI/coding agents against CI/CD and incident workflows with deterministic execution, approval gates, replayable evidence, and measurable ROI.

The broader personal assistant vision remains, but the current commercial stage prioritizes one saleable pilot loop: select a PR/CI scenario, run a release gate, export evidence, review ROI, and decide whether the buyer should upgrade to Power.

## Working Style
- Plan before coding for non-trivial tasks
- Prefer small incremental changes
- Keep code readable and modular
- Avoid premature abstraction
- Every important feature should be testable

## Tech Stack
- Frontend: Next.js + React + TypeScript
- Backend: FastAPI + Python
- Database: PostgreSQL
- Optional: vector store for semantic retrieval
- Current orchestration entities: `WorkflowOrchestration`, `WorkflowStepRun`, `WorkflowTemplate`
- Current orchestration queue entity: `WorkflowQueueJob`
- Current orchestration routes: `/api/orchestrations/*`

## Repository Structure
- `frontend/`: UI
- `backend/`: APIs, services, agent orchestration
- `docs/`: architecture and workflow docs
- `tests/`: automated tests

## Coding Conventions
- Write simple, explicit code
- Prefer composition over deep inheritance
- Add docstrings/comments only where helpful
- Keep functions focused, single responsibility
- Avoid hidden side effects
- Keep orchestration outputs deterministic and inspectable (no opaque free-form-only responses)

## Security Baseline
- Keep sensitive input (tokens, passwords, secrets) out of plain logs.
- Add guardrails for oversized payloads and abusive request patterns.
- Prefer deterministic validation errors over silent truncation in user-facing APIs.
- Keep externally exposed deployment paths minimal and easy to audit.
- For orchestration/audit payloads, preserve explainability (`conclusion/evidence/risk/next_action`) while sanitizing sensitive strings.
- Prefer signed entitlement (`X-Entitlement`) over plain tier headers for subscription-bound orchestration actions.

## Commercial Pilot Rules
- Keep `/dashboard`, `/orchestrate`, `/orchestrations`, `/monetization`, and `/tutorial` aligned as one buyer journey.
- Any orchestration commercial change must verify pilot scenario loading, ROI aggregation, evidence export, and tier/approval boundaries together.
- Pilot scenario data is static and auditable in V1; do not add OAuth, private repo pulls, Stripe, login, or RBAC unless explicitly requested.
- Manual Billing V1 remains the commercial adapter until the pilot package proves buyer value.
- Evidence bundles and pilot reports must stay redaction-safe and must not include raw entitlement tokens, passwords, secrets, or private credentials.
- Pilot Closeout is the current buyer-facing finish line: scenario completion, missing evidence, ROI, and Power upgrade evidence must stay consistent across `/tutorial`, `/orchestrations`, `/monetization`, and `/dashboard`.
- Commercial reporting endpoints must be read-only unless explicitly named as checkout, cancel, reactivate, or usage-recording paths.

## Task Expectations
When given a task:
1. understand the goal
2. identify impacted modules
3. propose a short plan
4. implement incrementally
5. run relevant tests
6. update docs if behavior changes
7. confirm with the user if the task is completed
8. for orchestration changes, explicitly verify:
   - step replay integrity
   - partial-success behavior
   - tier boundary behavior (`free` vs `pro/power`)
   - queue lifecycle behavior (`queued/running/succeeded/failed/canceled`) and retry/cancel idempotency
   - pilot scenario behavior (`GET /api/orchestrations/pilot-scenarios`, `/orchestrate?scenario=...`)
   - pilot readiness reporting (`GET /api/monetization/pilot-report`)
   - pilot closeout reporting (`GET /api/monetization/pilot-closeout`)
   - ROI and evidence export behavior (`GET /api/orchestrations/{id}/evidence`)

## Do Not
- do not introduce unrelated refactors
- do not silently change architecture without documenting it
- do not skip tests for core flows
- do not perform risky external actions without approval
- do not break existing `/plans/*`, `/analysis/*`, `/reflections/*` compatibility when extending orchestration

## Definition of Done
A task is done when:
- implementation is complete
- tests pass
- key edge cases are handled
- docs are updated if needed
- output can be manually verified
- if orchestration is touched, API + UI + replay/history tests are updated together
