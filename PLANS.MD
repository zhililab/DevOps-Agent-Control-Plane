# PLANS.md

## Project
Personal Agent Assistant

## Project Goal
Build a personal AI agent assistant that helps the user turn context into action across work, learning, life planning, reflection, and communication.

The system should first become a reliable daily-use MVP, then evolve into a reusable personal operating system.

---

# 0. Current Iteration Snapshot (2026-04-21)

## Theme Upgrade (In Progress)
- target style: Obsidian-like visual language (dark canvas, violet accent, layered cards, knowledge graph feeling)
- status: frontend visual redesign is underway and already runnable locally

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
- recorded local timing proxy for CI split:
  - `make test` real time: `~2.21s`
  - `make qa-fast` real time: `~7.59s` (includes frontend production build)

## Next Tasks
- run full k8s gate on a reachable cluster context (`make k8s-dry-run` currently blocked by cluster connectivity on local env)
- add pixel-level screenshot baseline (Playwright) on top of current DOM snapshot baseline
- add automated smoke checks for `/today`, `/reflection`, `/technical-analysis` after `make dev-up`
- verify k3d deployment path on target server and capture rollout evidence in docs
- verify simplified server deployment (`make server-deploy`) on target host and capture access URL

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

## MVP North Star
A user can:
1. define profile and preferences
2. generate a daily plan
3. generate a daily summary
4. save and review history
5. analyze a technical problem
6. generate communication drafts

---

# 3. Current Scope

## In Scope for MVP
- repository scaffold
- backend skeleton
- frontend skeleton
- profile management
- daily planning workflow
- daily reflection workflow
- persistence and retrieval
- technical analysis workflow
- communication draft workflow
- basic history and knowledge storage

## Out of Scope for MVP
- autonomous external actions
- heavy multi-agent orchestration
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

# 11. Recommended Daily Entry Point

## Primary Entry Point
Today page

## Why
The Today page connects:
- work execution
- meetings
- blockers
- task prioritization
- status generation
- evening reflection

This should become the most frequently used page in the MVP.

---

# 12. Definition of Done for MVP

The MVP is complete when all of the following are true:

- profile and preferences can be managed
- daily plan can be generated and saved
- daily reflection can be generated and saved
- history can be reviewed
- technical analysis can be generated and saved
- communication drafts can be generated and saved
- weekly review can be generated
- core workflows have tests
- setup docs are clear
- the app can run locally end to end

---

# 13. Immediate Next Action

## Recommended Next Step
Start with:
1. P0 Bootstrap
2. P1 Core Backend and Frontend Skeleton

Do not start multiple advanced phases in parallel before the core daily-use workflows are stable.
