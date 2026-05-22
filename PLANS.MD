# PLANS.md

## Project
Personal Agent Assistant

## Project Goal
Build a personal AI agent assistant that helps the user turn context into action across work, learning, life planning, reflection, and communication.

The long-term vision remains a reusable personal operating system for execution, reflection, and repeatable workflows.

Current iteration goal: close out and ship the DevOps orchestration MVP. The current deployable product is centered on deterministic multi-agent orchestration for personal DevOps workflows, with inspectable step replay/history, queue lifecycle visibility, signed entitlement-aware tier gates, and reusable knowledge/templates. Communication Assistant and Weekly Review remain planned product modules, but they are not blockers for the current DevOps orchestration MVP deployment.

---

# 0. Current Iteration Snapshot (2026-05-21)

## Iteration Theme
- current iteration target: DevOps orchestration MVP launch closeout
- product direction: deterministic personal DevOps orchestration with inspectable replay, queue lifecycle visibility, signed entitlement-aware tier gates, and reusable knowledge/templates
- UI direction: Obsidian-like visual language remains the active baseline (dark canvas, violet accent, layered cards, knowledge graph feeling)
- status: core orchestration, queue, entitlement, monetization observability, knowledge, and template foundations are implemented and covered by focused tests; the Docker Compose server deployment path is the current MVP release path, with k3d/k8s retained as follow-up deployment options

## Completed In This Iteration
- added route-level cinematic transition layer
- upgraded dashboard with a knowledge-graph visualization card
- switched core UI palette to dark + violet accent style
- kept charts, KPI blocks, and forms compatible with current workflows
- implemented Obsidian-style Hero with large gradient headline and layered glass panels
- added graph focus filters: All / Plan / Reflection / Analysis with visual highlight
- added scroll-triggered narrative section animation for landing-like storytelling
- added template bootstrap import system (JSON/SQL API + local import commands)
- imported first curated template pack (22 items) into current local database
- improved mobile readability and contrast guardrails (dashboard, graph, status, pre blocks)
- added keyboard-operable graph focus interactions with active/dim consistency
- added visual baseline tests for dashboard and knowledge pages
- expanded visual baseline tests to include Today/Reflection generated-result states
- added parallel QA commands: `make qa-fast`, `make qa-visual`, `make qa-all`
- upgraded CI pipeline to parallel jobs with `integration-gate`
- added visual style and token documentation: `docs/visual-guidelines.md`
- added release checklist and command gate: `docs/release-checklist.md` + `make release-check`
- added automated smoke gate: `make smoke-check` for key routes + core workflow APIs
- extended smoke checks with response-shape assertions for knowledge/templates listing APIs
- added k3d online deployment path for older kernels: `scripts/deploy_k3d_online.sh` + `make k3d-deploy`
- added simplified always-on server deployment path: `docker-compose.server.yml` + `make server-deploy`
- added deterministic multi-agent orchestration workflow (Planner/Analyzer/Reviewer)
- added orchestration persistence entities: `WorkflowOrchestration`, `WorkflowStepRun`, `WorkflowTemplate`
- added orchestration queue persistence entities: `WorkflowQueueJob`, `WorkflowQueueEvent`
- added monetization persistence entities: `SubscriptionProfile`, `UsageCounter`, `MonetizationEvent`
- added orchestration APIs:
  - `POST /api/orchestrations/run`
  - `GET /api/orchestrations/history`
  - `GET /api/orchestrations/{id}`
  - `GET /api/orchestrations/metrics?days=...`
  - `GET /api/orchestrations/entitlement/bootstrap`
  - `POST /api/orchestrations/queue/run`
  - `GET /api/orchestrations/queue/history`
  - `GET /api/orchestrations/queue/{job_id}`
  - `POST /api/orchestrations/queue/{job_id}/retry`
  - `POST /api/orchestrations/queue/{job_id}/cancel`
  - template CRUD/import/export under `/api/orchestrations/templates*`
- added orchestration UI pages:
  - `/orchestrate` (run + replay + template operations)
  - `/orchestrations` (history + filter + queue job list + timeline replay)
- added free/pro/power tier gate (free single-step restriction for orchestration runs)
- added signed entitlement verification path (`X-Entitlement`) with config switch for required mode
- added production behavior that requires signed entitlement and disables legacy tier fallback
- added non-production legacy `X-Subscription-Tier` fallback only when explicitly enabled
- removed legacy `X-Subscription-Tier` emission from the `/orchestrate` frontend caller; the UI now uses signed entitlement token/default backend resolution
- added local entitlement token helper and optional public bootstrap endpoint
- added partial-success fallback strategy (step failure does not abort full workflow)
- added reusable output persistence bridge from orchestration to knowledge/templates
- added orchestration backend and frontend test coverage
- added monetization/observability contract tests for:
  - entitlement expired + signature mismatch handling
  - token-vs-legacy tier mismatch precedence
  - free-tier capability deny in queued orchestration execution
  - quota boundary (`429`) behavior on orchestration metrics endpoint
  - orchestration metrics response shape + deterministic history ordering checks
- added frontend dashboard monetization KPI render/fallback contract tests
- added observability API route for monetization aggregation: `GET /api/observability/monetization?days=7|30`
- added dedicated monetization read APIs:
  - `GET /api/monetization/profile?subject=...`
  - `GET /api/monetization/usage?subject=...`
  - `GET /api/monetization/events?limit=...`
- aligned frontend monetization observability client with backend canonical route: `/api/observability/monetization`
- upgraded `/orchestrate` UI with sync/async run mode, queue job status card, retry/cancel actions
- upgraded `/orchestrations` UI with queue status filtering and timeline replay from `WorkflowQueueEvent`
- connected retry/cancel controls into dedicated `/orchestrations` queue history view
- upgraded dashboard orchestration KPI visualization with 7D/30D window switch
- extended automated smoke checks to cover orchestration metrics, queue run/history, monetization observability, and monetization read APIs
- verified extended local smoke checks against dev stack with signed entitlement token
- verified local Kubernetes manifest rendering with `make k8s-render` (275 rendered lines); `make k8s-dry-run` still requires a reachable cluster context
- added real-browser orchestration E2E coverage for `/orchestrate -> /orchestrations` with Playwright and an isolated local test stack
- added core functionality check document: `docs/core-functionality-check.md`
- added security hardening and robustness gate: `make security-check`
- added gateway security headers, report-only CSP, configurable production CORS, and hidden frontend `X-Powered-By`
- upgraded frontend security patch dependencies: Next `15.5.18`, React/ReactDOM `19.2.6`, Vitest `2.1.9`
- added immutable orchestration history ledger for accuracy-first audit storage:
  - `history_events` table with canonical JSON payloads, SHA-256 verification, source references, and previous-event hash pointer
  - orchestration accepted/completed, step success/failure/skipped, queue lifecycle, and monetization policy/usage events write ledger snapshots
  - idempotent backfill from existing orchestration, step, queue, queue event, and monetization agent-log records
  - read-only integrity API: `GET /api/orchestrations/{id}/history-events`
  - `/orchestrations` UI can verify and display ledger integrity status/event count per run
- added history time accuracy and storage hygiene pass:
  - `APP_BUSINESS_TIMEZONE=Asia/Shanghai` as the business-date source of truth
  - UTC-marked public timestamps for API datetime fields
  - `record_source` and `business_timezone` metadata on daily plan, reflection, and technical analysis records
  - safe migration/backfill to recalculate historical business dates from UTC timestamps
  - default personal history views hide smoke/system records while `include_system=true` keeps audit access
  - read-only history endpoints no longer write `agent_run_logs`
- added query performance optimization pass:
  - batched `/api/orchestrations/history` step replay loading to remove N+1 step queries
  - optional `include_steps=false` lightweight orchestration history reads for dashboard/trend views
  - SQL aggregate orchestration metrics instead of Python-side full-window scans
  - composite indexes for orchestration history filters, step replay lookup, queue history filters, queue event timelines, monetization logs, and history ledger integrity lookups
  - backend regression tests for batched step loading, lightweight history reads, aggregate metrics, and stable queue ordering
- updated release gate to use the current server-release path: `make qa-all`, `make e2e-orchestration`, `make security-check`, and `make k8s-render`
- verified simplified server deployment on target host with `make server-deploy`
  - deployed commit: `1e005db chore: release deploy 2026-05-21-2255`
  - follow-up docs/script health-path commit: `eb32a17 docs: align deployment health check path`
  - server: `http://1.117.63.81`
  - health: `http://1.117.63.81/health`
  - verified public routes: `/dashboard`, `/orchestrate`, `/orchestrations`
  - remote smoke checks passed for core pages, core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, and monetization read APIs
- recorded local timing proxy for CI split:
  - `make test` real time: `~2.21s`
  - `make qa-fast` real time: `~7.59s` (includes frontend production build)

## Still Pending / Next Tasks

### Launch Required
- keep `make qa-all`, `make e2e-orchestration`, `make security-check`, and server smoke checks green before each release
- capture any future production deployment run in `docs/deployment-evidence.md`
- keep orchestration history ledger backfill idempotent and integrity checks valid before production deploys
- take a PostgreSQL backup before running history/data migrations on the remote server; routine releases keep `REMOTE_RESET_DB=0`

### UX Closeout
- add orchestration replay UX V2 (timeline/diff view + richer failure drill-down)
- extend dashboard KPI trend from bar-only to line+delta insights with anomaly hinting
- add pixel-level screenshot baseline (Playwright) on top of current DOM snapshot baseline
- verify k3d deployment path on target server and capture rollout evidence in docs
- run full k8s gate on a reachable cluster context when a Kubernetes deployment becomes the selected release path

### Later Product Completion
- complete P7 Communication Assistant (not a current deployment blocker)
- complete P8 Weekly Review (not a current deployment blocker)
- continue P9 integrations foundation after the orchestration MVP is deployed and audited

---

# 1. Working Rules

## Execution Principles
- Prefer incremental progress over large rewrites
- Keep each task small enough to validate quickly
- Prioritize testability, readability, consistency, then simplicity
- Do not overbuild architecture before core workflows are stable
- Always keep at least one end-to-end flow working
- For non-trivial tasks, plan before coding
- When stuck after repeated failed attempts, record blockers and propose alternatives

## Delivery Principles
- Each phase must produce something demoable
- Each task should have clear acceptance criteria
- Every completed feature should be testable locally
- Important workflow changes must update docs

## Reporting Expectations
At the end of each meaningful task, report:
- what changed
- files touched
- tests run
- current limitations
- suggested next step

---

# 2. North Star

## Product North Star
Turn scattered thoughts, tasks, and problems into:
- structured plans
- actionable next steps
- reusable knowledge
- reflective feedback loops

## Original MVP North Star
A user can:
1. define profile and preferences
2. generate a daily plan
3. generate a daily summary
4. save and review history
5. analyze a technical problem
6. generate communication drafts

## Current DevOps Orchestration MVP North Star
A user can run a deterministic DevOps workflow, inspect every step and queue event, replay history, reuse templates/knowledge, and operate within clear free/pro/power entitlement boundaries.

---

# 3. Current Scope

## In Scope for Current DevOps Orchestration MVP
- repository scaffold
- backend skeleton
- frontend skeleton
- profile management
- daily planning workflow
- daily reflection workflow
- persistence and retrieval
- technical analysis workflow
- basic history and knowledge storage
- deterministic multi-agent orchestration workflow
- orchestration step replay and history retrieval
- orchestration template CRUD/import/export
- lightweight SaaS tier boundary (free/pro/power gate for orchestration)
- signed entitlement enforcement for production orchestration actions
- queue lifecycle visibility for queued/running/succeeded/failed/canceled jobs
- deployment-ready smoke/release validation for orchestration APIs and pages

## Planned but Not Blocking Current Deployment
- communication draft workflow
- weekly review workflow

## Out of Scope for Current DevOps Orchestration MVP
- autonomous external actions
- autonomous multi-agent self-planning without user-provided context
- advanced vector retrieval
- full calendar/email/Jira sync
- mobile app
- deep workflow automation across third-party systems

---

# 4. Execution Strategy

## Strategy
Build from inner loop to outer loop.

Order of implementation:
1. scaffold
2. data model
3. profile
4. daily planning
5. daily reflection
6. history
7. technical analysis
8. knowledge/templates
9. communication assistant
10. external integrations

## Why this order
This order ensures:
- the system becomes usable early
- the most frequent daily workflows land first
- later features build on stable data and UI foundations
- complexity grows only after value is proven

---

# 5. Phase Plan Overview

## Roadmap Status
The P0-P9 roadmap remains the long-term product map. The current codebase has moved beyond the early daily-use MVP foundation and is now in DevOps orchestration MVP launch closeout. P7 Communication Assistant and P8 Weekly Review are still pending product modules, but they are not required before the current orchestration deployment.

| Phase | Name | Goal | Demo Output |
|------|------|------|-------------|
| P0 | Bootstrap | Create repository and development skeleton | Repo starts locally |
| P1 | Core Backend/Frontend | Establish app structure and core data model | App shells and APIs run |
| P2 | Daily Plan MVP | Build first end-to-end planning workflow | Generate and save daily plan |
| P3 | Daily Reflection MVP | Build end-of-day summary workflow | Generate and save reflection |
| P4 | History & Persistence | Make results durable and reviewable | View past plans and summaries |
| P5 | Technical Analysis | Support structured DevOps problem solving | Analyze and save issue breakdown |
| P6 | Knowledge & Templates | Store reusable outputs and prompts | Create and browse notes/templates |
| P7 | Communication Assistant | Generate better conversation drafts | Multi-style message generation |
| P8 | Weekly Review | Generate weekly reports and patterns | Weekly reflection report |
| P9 | Integrations Foundation | Prepare external system integration layer | Integration-ready architecture |

---

# 6. Detailed Execution Plans

## P0 - Bootstrap

### Goal
Create a clean repository and local development environment that supports iterative delivery.

### Tasks
- create repository structure
- add README.md
- add AGENTS.md
- add specs.md
- add PLANS.md
- add .env.example
- add Makefile
- add docker-compose.yml
- add docs skeleton
- add scripts skeleton
- add CI placeholder workflows

### Acceptance Criteria
- repository structure exists
- local setup instructions exist
- PostgreSQL can be started locally
- frontend and backend folders are ready
- docs structure exists

### Deliverables
- working repo scaffold
- runnable local dev instructions

### Risks
- overcomplicating structure too early
- adding tools before needed

### Notes
Keep initial structure simple and practical.

---

## P1 - Core Backend and Frontend Skeleton

### Goal
Create the minimal application architecture for both frontend and backend.

### Backend Tasks
- set up FastAPI app
- set up config loading
- set up DB session/base
- set up Alembic
- add health route
- add API router structure
- add base models and schemas

### Frontend Tasks
- set up Next.js app
- add base layout
- add navigation
- add empty pages:
  - dashboard
  - profile
  - today
  - reflection
  - analysis
  - communication
  - history
- add API client utilities

### Acceptance Criteria
- backend starts locally
- frontend starts locally
- health endpoint works
- basic navigation works
- folder structure is stable enough for feature work

### Deliverables
- frontend shell
- backend shell
- initial model/router scaffolding

### Risks
- leaking business logic into routes/pages
- unstable contracts between frontend and backend

### Notes
Keep handlers thin and components small.

---

## P2 - Daily Plan MVP

### Goal
Implement the first high-value closed loop:
input daily context -> generate plan -> save result -> view result

### Backend Tasks
- define daily plan request/response schema
- implement planning endpoint
- implement planning service
- persist generated plan
- add agent run logging for plan generation

### Frontend Tasks
- build Today page form
- add input fields:
  - tasks
  - meetings
  - blockers
  - priorities
- display generated structured plan
- add save confirmation / history access

### Expected Output Structure
- top priorities
- execution order
- blockers and risks
- next actions
- concise daily status summary

### Acceptance Criteria
- user can submit daily context
- system generates structured daily plan
- plan is persisted
- saved plan can be viewed later

### Deliverables
- first end-to-end usable workflow

### Risks
- output too generic
- weak persistence model
- unclear UI state transitions

### Notes
This is the first real proof of product value.

---

## P3 - Daily Reflection MVP

### Goal
Implement the second daily-use closed loop:
input day outcome -> generate summary -> save reflection -> retrieve later

### Backend Tasks
- define reflection schema
- implement reflection endpoint
- implement reflection service
- persist reflection entry
- log reflection runs

### Frontend Tasks
- build Reflection page form
- add input fields:
  - completed work
  - unfinished work
  - blockers
  - notes
  - mood
- display generated summary and next-step suggestions

### Expected Output Structure
- day summary
- unfinished items
- patterns noticed
- suggested tomorrow focus

### Acceptance Criteria
- user can submit reflection input
- summary is generated
- reflection is saved
- history retrieval works

### Deliverables
- second end-to-end core workflow

### Risks
- outputs becoming repetitive
- not capturing enough structured context

### Notes
This phase creates the first true improvement loop.

---

## P4 - History and Persistence

### Goal
Make the system durable so that outputs become reusable over time.

### Tasks
- design history retrieval APIs
- add listing pages/cards for prior plans/reflections
- add filtering by type/date
- improve DB schema where needed
- ensure saved results are linked to run logs

### Acceptance Criteria
- user can view prior daily plans
- user can view prior reflections
- history is understandable and navigable
- saved data supports later weekly review

### Deliverables
- usable history view
- persistence foundation for later features

### Risks
- weak retrieval UX
- inconsistent saved object structure

### Notes
Without persistence, the assistant stays disposable.

---

## P5 - Technical Analysis Workflow

### Goal
Provide a structured assistant for DevOps and engineering problem-solving.

### Input Types
- logs
- errors
- code snippets
- issue descriptions
- incident notes

### Output Structure
- problem statement
- likely causes
- validation steps
- fix options
- risks
- follow-up tasks

### Backend Tasks
- add analysis schema
- implement analysis endpoint
- implement analysis service
- persist analysis results

### Frontend Tasks
- build Analysis page
- add structured result display
- support saving to history

### Acceptance Criteria
- technical issue can be submitted
- structured analysis is generated
- result is saved
- basic tests cover request validation and persistence

### Deliverables
- technical assistant MVP

### Risks
- shallow generic suggestions
- poor formatting for long logs/errors

### Notes
This phase directly serves the highest-value work scenario.

---

## P6 - Knowledge and Templates

### Goal
Turn useful outputs into reusable assets.

### Tasks
- add NoteEntry model and APIs
- add PromptTemplate model and APIs
- build UI for listing and creating notes/templates
- support tags
- support simple filtering/search
- allow saving useful generated outputs into knowledge entries

### Acceptance Criteria
- notes can be created and viewed
- templates can be created and edited
- tags and filters work
- saved outputs can be promoted into durable knowledge

### Deliverables
- reusable knowledge base foundation

### Risks
- building too much search complexity too early
- mixing transient history with durable knowledge

### Notes
History records what happened; knowledge captures what should be reused.

---

## P7 - Communication Assistant

### Goal
Support better drafting for sensitive or important communication.

### Input
- scenario description
- target person/context
- desired tone
- optional facts and concerns

### Output Modes
- empathetic
- direct
- boundary-setting

### Optional Structure
- facts
- feelings
- needs
- requests

### Tasks
- add communication endpoint
- implement generation service
- build frontend page
- save generated drafts to history
- support choosing style mode

### Acceptance Criteria
- scenario can be submitted
- multiple draft styles are generated
- drafts can be reviewed and saved

### Deliverables
- communication support workflow

### Risks
- drafts sounding robotic
- poor differentiation between styles

### Notes
This module should help shift from pure information delivery toward better connection and expression.

---

## P8 - Weekly Review

### Goal
Create a weekly reflective summary across saved activity.

### Inputs
- recent plans
- recent reflections
- task status
- optional free-text notes

### Output Structure
- what progressed
- what stalled
- recurring patterns
- next-week focus
- suggested improvement actions

### Tasks
- add weekly review endpoint
- aggregate recent data
- generate weekly review output
- save weekly reports
- add weekly review page

### Acceptance Criteria
- weekly report can be generated
- report is saved
- report uses recent saved data
- report is readable and actionable

### Deliverables
- first medium-range reflective loop

### Risks
- too much generic summarization
- poor signal from earlier saved data

### Notes
This phase transforms isolated daily use into a growth system.

---

## P9 - Integrations Foundation

### Goal
Prepare architecture for future integrations without overbuilding.

### Candidate Integrations
- calendar
- email
- Jira
- Git hosting
- note systems
- messaging platforms

### Tasks
- define integration abstraction layer
- define approval flow for risky actions
- add audit logging for external actions
- document integration strategy

### Acceptance Criteria
- architecture supports future integrations
- no risky automation is enabled by default
- approval design is documented

### Deliverables
- safe extension foundation

### Risks
- integration-first thinking too early
- accidental side effects

### Notes
Do not implement broad integrations before core internal workflows are stable.

---

# 7. Suggested Iteration Plan

This is the preserved long-term phase sequencing. The current iteration has already advanced beyond the early MVP phases and is focused on DevOps orchestration launch closeout, not restarting at Iteration 1.

## Iteration 1
Focus:
- P0
- P1

Target outcome:
- project boots locally
- app shells exist

## Iteration 2
Focus:
- P2

Target outcome:
- daily plan end-to-end works

## Iteration 3
Focus:
- P3
- P4

Target outcome:
- daily summary works
- history is usable

## Iteration 4
Focus:
- P5

Target outcome:
- technical analysis workflow works

## Iteration 5
Focus:
- P6
- P7

Target outcome:
- reusable knowledge and communication support land

## Iteration 6
Focus:
- P8
- P9

Target outcome:
- weekly review exists
- future integration path is defined

---

# 8. Task Sizing Guidance

## Small Task
- 1 file or 1 focused change
- can complete without architecture change
- no plan document needed

## Medium Task
- touches several files
- affects one workflow
- requires short implementation plan

## Large Task
- affects multiple modules
- changes schema/contracts/architecture
- requires explicit plan before coding
- should be split into sub-steps

---

# 9. Validation Checklist

Before marking a task done, verify:

- feature works locally
- core path is tested
- error handling exists
- docs are updated if needed
- code stays understandable
- scope remains focused
- next step is clear

---

# 10. Known Product Risks

## Product Risks
- becoming a collection of unrelated AI features
- weak differentiation between history, knowledge, and templates
- too much emphasis on generation, too little on workflow closure

## Engineering Risks
- premature abstractions
- backend/frontend contract drift
- insufficient persistence design
- weak observability for agent runs

## Execution Risks
- too many features in parallel
- missing demoable milestones
- no stable “daily use” entry point

---

# 11. Recommended Entry Points

## Current Orchestration Entry Points
- `/orchestrate` for running sync/async orchestration and operating queue actions
- `/orchestrations` for history, filtering, queue status review, and timeline replay

## Original Daily Entry Point
Today page

## Why
The Today page connects:
- work execution
- meetings
- blockers
- task prioritization
- status generation
- evening reflection

The Today page remains the daily planning/reflection entry point for the broader personal assistant vision. For the current DevOps orchestration MVP, `/orchestrate` and `/orchestrations` are the primary deployment validation surfaces.

---

# 12. Definition of Done for Current DevOps Orchestration MVP

The current DevOps orchestration MVP is deployable when all of the following are true:

- technical analysis can be generated and saved
- orchestration runs are deterministic and persist inspectable step outputs
- replay/history views show orchestration and queue lifecycle state clearly
- partial-success behavior is tested and understandable
- retry/cancel behavior is idempotent across queued/running/succeeded/failed/canceled states
- free/pro/power tier boundaries are enforced through signed entitlement in production
- legacy `X-Subscription-Tier` behavior is limited to explicitly enabled non-production paths
- orchestration APIs/pages are covered by focused backend/frontend tests and smoke checks
- deployment evidence is captured for the chosen server path
- setup docs are clear
- the app can run locally end to end
- Communication Assistant and Weekly Review remain incomplete but are explicitly non-blocking for this deployment

---

# 13. Immediate Next Action

## Recommended Next Step
Close the DevOps orchestration MVP launch gate in priority order:
1. keep `/orchestrate -> /orchestrations` E2E coverage green
2. keep server deployment evidence current after each `make release-deploy`
3. verify extended smoke checks against the deployed gateway
4. defer Communication Assistant and Weekly Review until after the orchestration MVP is deployed
