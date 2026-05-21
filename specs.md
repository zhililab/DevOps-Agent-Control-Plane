# Personal Agent Assistant - Product Specs

## 1. Overview

This project builds a personal AI agent assistant for a DevOps-oriented user.
The long-term product direction is a personal AI operating system: a durable layer for execution, reflection, knowledge, communication, and reusable workflows.

The current MVP narrows that vision into a deterministic DevOps personal workflow orchestration product. It focuses on turning repeatable work patterns into inspectable, replayable, and tier-aware workflows rather than trying to deliver every personal assistant capability at once.

The long-term assistant is not just a chatbot. It should help the user:

- manage work tasks and priorities
- convert ideas into actionable plans
- support DevOps / platform engineering workflows
- organize personal learning and long-term growth
- assist with life planning, travel, and relationship communication
- generate summaries, retrospectives, and next-step suggestions

The system must focus on practical execution, structured thinking, and continuous iteration.

---

## 2. Product Vision

Build toward a personal AI operating system that acts like a combination of:

- personal chief of staff
- DevOps copilot
- planning and reflection coach
- knowledge organizer
- execution tracker

The long-term system should help the user reduce cognitive load, improve follow-through, and continuously refine work and life workflows.

The current product layer is the DevOps workflow orchestration MVP. Its purpose is to provide a reliable execution substrate for personal DevOps workflows:

- define workflow templates
- create orchestration runs from templates or requests
- execute steps deterministically
- preserve structured outputs for replay, audit, and history
- handle partial success, retries, cancellation, and queue lifecycle states
- enforce subscription/tier boundaries for advanced orchestration actions

Daily planning, reflection, knowledge capture, communication support, and weekly review remain part of the long-term operating-system vision. In the current MVP, only the parts directly connected to workflow planning, execution history, and inspectable orchestration outputs should be treated as landed.

---

## 3. Target User

Primary target user:

- Senior DevOps / Platform / Infrastructure engineer
- Works in EDA-related engineering environment
- Handles Jenkins, Bitbucket, CI/CD, build systems, monitoring, automation, and infrastructure tasks
- Wants to grow from task executor to platform-level thinker
- Needs support across work, learning, life planning, and interpersonal communication

---

## 4. Core Design Principles

1. Incremental progress over big-bang redesign
2. Clarity over cleverness
3. Actionable output over abstract discussion
4. Small closed loops over vague long-term intentions
5. Reusable workflows over one-off answers
6. Testability over intuition
7. Readability and consistency over premature complexity

---

## 5. Product Goals

### 5.1 Current MVP: DevOps Workflow Orchestration
The current MVP should help the user:
- turn recurring DevOps/platform workflows into structured templates
- launch workflow orchestrations from explicit inputs
- track orchestration and step state from queued through terminal outcomes
- inspect deterministic step outputs with conclusion, evidence, risk, and next action
- replay completed or partially completed workflows without losing step integrity
- safely retry or cancel queued/running work with idempotent behavior
- keep free vs pro/power behavior explicit for subscription-bound features

### 5.2 Long-Term: Work Assistance
The agent should help the user:
- break down technical work into concrete tasks
- draft implementation plans and review checklists
- summarize incidents, root causes, and follow-up actions
- generate meeting briefs and progress updates
- support DevOps/platform engineering decision-making
- identify reusable patterns from repeated work

Current status:
- Landed / in progress: deterministic workflow orchestration, templates, queue jobs, run history, structured step outputs
- Not yet fully landed: broad meeting briefs, incident retrospectives, external DevOps system integrations

### 5.3 Long-Term: Learning Assistance
The agent should help the user:
- convert technical topics into structured learning plans
- explain complex documents in simple language
- build reusable prompt templates and note structures
- extract transferable methods from specific cases

Current status:
- Partially supported when learning output is represented as a workflow or reusable template
- Not yet a standalone learning companion product surface

### 5.4 Long-Term: Personal Planning
The agent should help the user:
- create daily / weekly / monthly plans
- generate reminders and summaries
- track habits, routines, and priorities
- support travel planning, packing, and scheduling

Current status:
- Preserved as product direction
- Not yet fully landed as calendar-aware planning, reminders, habit tracking, or travel planning

### 5.5 Long-Term: Relationship / Communication Support
The agent should help the user:
- prepare emotionally aware communication drafts
- improve expression, empathy, and boundaries
- reflect on conversation patterns
- shift from “problem solving mode” to “connection mode” when needed

Current status:
- Preserved as long-term direction
- Communication Assistant should not be described as complete in the current MVP

### 5.6 Long-Term: Reflection and Growth
The agent should help the user:
- generate daily summary and suggested next steps
- produce weekly reflection reports
- detect recurring friction and bottlenecks
- convert outcomes into workflow improvements

Current status:
- Partially supported through orchestration history, run outputs, and replay/audit data
- Daily summary and Weekly Review are long-term goals unless explicitly backed by workflow templates and tested product flows

---

## 6. Non-Goals

The first version should NOT try to:
- fully automate every external system
- replace all note-taking tools
- become a general social network manager
- perform autonomous high-risk actions without explicit approval
- over-engineer memory, ranking, or agent orchestration before the core loop works

---

## 7. Key User Problems

1. Too many ideas but weak execution closure
2. Work tasks are often discussed but not systematically broken down
3. Repeated technical issues are not always turned into reusable workflows
4. Daily summaries and planning are inconsistent
5. Emotional / relationship conversations often stay at information level instead of feeling level
6. Knowledge is accumulated, but not well organized into action patterns
7. Need a single personal system that connects work, learning, life, and growth

---

## 8. Core User Scenarios

### Scenario A: Daily Work Planning
Input:
- today’s tasks, blockers, meetings, priorities

Output:
- prioritized plan
- risk reminders
- concise status update draft
- suggested next actions

### Scenario B: Technical Problem Solving
Input:
- logs, code snippets, pipeline failures, architecture problems

Output:
- structured problem breakdown
- hypotheses
- debugging plan
- implementation suggestions
- follow-up checklist
- retrospective template

### Scenario C: Weekly Reflection
Input:
- completed work, unfinished work, emotional state, lessons learned

Output:
- summary
- pattern analysis
- what to continue / stop / improve
- next week focus

### Scenario D: Learning Companion
Input:
- technical topic, article, doc, repo, architecture question

Output:
- simplified explanation
- why it matters
- learning path
- practical exercises
- transferable principles

### Scenario E: Relationship / Communication Support
Input:
- recent interaction context
- emotional confusion or communication difficulty

Output:
- hidden emotional dynamics analysis
- better communication options
- empathy-oriented message drafts
- self-reflection prompts

---

## 9. MVP Scope

The MVP scope is the DevOps personal workflow orchestration layer. It should support deterministic creation, execution, inspection, replay, retry, and cancellation of workflow runs.

Capabilities outside that layer remain long-term product vision unless they are implemented as workflow templates on top of the orchestration system.

### 9.1 Input Layer
- text input
- structured orchestration creation requests
- workflow template selection and parameter input
- optional file input only where implemented and validated by the workflow

### 9.2 Orchestration Layer
- `WorkflowTemplate` definitions for reusable work patterns
- `WorkflowOrchestration` runs for a specific execution
- `WorkflowStepRun` records for deterministic step state and outputs
- `WorkflowQueueJob` records for asynchronous queue lifecycle tracking
- replay/history APIs for inspectable prior execution

### 9.3 Execution and Queue Layer
- queue jobs through `queued`, `running`, `succeeded`, `failed`, and `canceled`
- retry and cancel behavior with idempotency
- partial-success handling when some steps complete and later steps fail
- deterministic validation errors for invalid or oversized requests

### 9.4 Output and Audit Layer
- structured step outputs with `conclusion`, `evidence`, `risk`, and `next_action`
- orchestration history views
- replay-safe persisted outputs
- sanitized audit payloads that avoid exposing secrets

### 9.5 Long-Term Personal OS Layers
- daily planning
- reflection and weekly review
- knowledge entries and retrieval
- communication drafting
- travel and life planning

These layers remain important product directions, but they are not all current MVP deliverables.

---

## 10. Functional Requirements

### FR-1 User Profile Management
The long-term system shall store and use:
- preferred response language
- preferred reasoning style
- work role and domain
- recurring workflows
- long-term goals
- communication preferences

Current MVP requirement:
- store and use only the profile/preferences needed to make orchestration behavior deterministic and inspectable

### FR-2 Workflow Template Management
The system shall:
- create and list reusable workflow templates
- define ordered workflow steps
- preserve template inputs and expected structured outputs
- keep templates understandable enough to audit and reuse

### FR-3 Workflow Orchestration Management
The system shall:
- create workflow orchestration runs
- persist run-level state and metadata
- persist step-level state and outputs
- expose orchestration history and detail views through `/api/orchestrations/*`
- support replay without mutating the original run history

### FR-4 Queue Lifecycle and Control
The system shall:
- create queue jobs for asynchronous orchestration work
- transition queue jobs through `queued`, `running`, `succeeded`, `failed`, and `canceled`
- support retry for failed or retryable work without duplicate side effects
- support cancel behavior for queued/running jobs with idempotent responses
- expose clear errors for invalid transitions

### FR-5 Deterministic Step Output
The system shall:
- return inspectable step outputs
- preserve `conclusion`, `evidence`, `risk`, and `next_action`
- sanitize secrets and sensitive strings from orchestration/audit payloads
- avoid opaque free-form-only responses for core orchestration steps

### FR-6 Tier and Entitlement Guardrails
The system shall:
- distinguish free vs pro/power orchestration behavior
- prefer signed entitlement (`X-Entitlement`) for subscription-bound actions
- return deterministic validation or authorization errors when limits are exceeded

### FR-7 Long-Term Planning and Reflection
The system should eventually:
- generate daily plans
- generate weekly focus suggestions
- generate end-of-day summaries
- generate weekly growth reports
- highlight recurring patterns
- suggest process improvements

Current MVP status:
- supported only where these outputs are implemented as workflow templates or orchestration history summaries
- Weekly Review should not be treated as a completed standalone module

### FR-8 Long-Term Personal Communication Assistant
The system should eventually:
- generate alternative message drafts
- support empathy-oriented phrasing
- help distinguish facts, feelings, needs, and requests

Current MVP status:
- preserved as a future product direction
- not complete as a dedicated Communication Assistant

### FR-9 Long-Term Knowledge Base
The system should eventually:
- save key outputs
- group outputs by domain
- support retrieval by topic
- support “what changed recently” views

Current MVP status:
- orchestration outputs and histories are saved for audit/replay
- broad knowledge retrieval and knowledge management remain future scope

### FR-10 Agent Task Workflow
The system shall:
- track open tasks
- track completed tasks
- support staged execution
- show progress state
- support manual approval for risky actions

---

## 11. Non-Functional Requirements

### NFR-1 Simplicity
The MVP should remain simple enough for one developer to understand and iterate quickly.

### NFR-2 Explainability
Every important suggestion should be understandable.
The system should explain why a recommendation is made.

### NFR-3 Auditability
Important actions and generated outputs should be logged with timestamps.

### NFR-4 Extensibility
The architecture should allow future integrations:
- calendar
- email
- Jira
- Git hosting
- note systems
- messaging platforms

### NFR-5 Safety
The system must require confirmation before sending messages, creating external records, or changing important data.

---

## 12. Suggested Architecture

### 12.1 Frontend
- React / Next.js
- dashboard-oriented UI
- orchestration dashboard, workflow template, queue, run detail, replay/history views
- long-term daily plan, reflection, knowledge, and communication views

### 12.2 Backend
- FastAPI
- modular service structure
- agent orchestration layer
- workflow template service
- orchestration run service
- step execution service
- queue job service
- entitlement and audit guardrails
- future memory, task, knowledge, and scheduling services

### 12.3 Data Storage
- PostgreSQL for structured data
- optional vector store for semantic retrieval
- file storage for uploads and generated artifacts

### 12.4 AI Layer
- current orchestration for deterministic DevOps workflow steps
- structured output adapters for conclusion, evidence, risk, and next action
- future specialized agents for planner, summarizer, reflective coach, technical analyst, and communication assistant

### 12.5 Integrations (future)
- Gmail / email
- calendar
- Jira
- GitHub / Bitbucket
- Feishu / WeChat / Slack
- local notes / markdown files

---

## 13. Initial Information Architecture

Current MVP modules:
- Dashboard
- Workflows
- Workflow Templates
- Orchestration Runs
- Queue Jobs
- Run History / Replay
- Settings

Long-term personal OS modules:
- Today
- Tasks
- Memory
- Knowledge
- Reflection
- Communication

---

## 14. MVP Screens

1. Orchestration dashboard
2. Workflow template list/detail page
3. Start orchestration page
4. Orchestration run detail page
5. Queue jobs page
6. Replay/history page
7. Settings / entitlement page

Future personal OS screens:
- Daily planning page
- Task board
- Reflection page
- Knowledge entries page
- Communication draft page

---

## 15. Data Model (Initial)

### UserProfile
- id
- name
- role
- language
- preferences_json
- goals_json
- created_at
- updated_at

### Task
- id
- title
- domain
- status
- priority
- source
- due_at
- context_json
- created_at
- updated_at

### NoteEntry
- id
- title
- category
- content
- tags_json
- source_type
- created_at
- updated_at

### ReflectionEntry
- id
- date
- summary
- patterns
- next_actions
- mood
- created_at
- updated_at

### PromptTemplate
- id
- name
- category
- content
- version
- created_at
- updated_at

### AgentRunLog
- id
- task_type
- input_summary
- output_summary
- status
- created_at

### WorkflowTemplate
- id
- name
- description
- category
- input_schema_json
- steps_json
- required_tier
- created_at
- updated_at

### WorkflowOrchestration
- id
- template_id
- status
- input_json
- output_json
- entitlement_tier
- created_at
- updated_at

### WorkflowStepRun
- id
- orchestration_id
- step_key
- status
- input_json
- output_json
- error_json
- started_at
- completed_at
- created_at
- updated_at

### WorkflowQueueJob
- id
- orchestration_id
- status
- attempts
- last_error_json
- queued_at
- started_at
- completed_at
- canceled_at
- created_at
- updated_at

---

## 16. MVP Success Metrics

### Product Metrics
- orchestration run can be created from a workflow template
- step outputs are structured, persisted, and replayable
- queue jobs move through expected lifecycle states
- partial success, retry, and cancel paths behave deterministically
- tier boundaries are enforced for subscription-bound orchestration actions
- repeated useful workflows are saved and reused

### User Value Metrics
- reduced planning friction
- more tasks are clearly decomposed
- better continuity between conversations
- more outputs are turned into action

---

## 17. Acceptance Criteria for MVP

The current orchestration MVP is considered successful when the user can:

1. create or select a workflow template for a DevOps personal workflow
2. start a workflow orchestration through `/api/orchestrations/*`
3. inspect each step run, including state and structured output
4. verify step replay integrity from persisted orchestration data
5. observe partial-success behavior when some steps complete and a later step fails
6. verify free vs pro/power tier boundary behavior for subscription-bound actions
7. track queue lifecycle states: `queued`, `running`, `succeeded`, `failed`, and `canceled`
8. retry failed or retryable work without duplicate side effects
9. cancel queued/running work idempotently
10. review a history of prior workflow runs and outputs

The following remain long-term personal AI operating-system acceptance criteria, not current MVP completion claims:

1. generate daily plans and summaries as a full standalone experience
2. generate weekly reflection reports as a completed Weekly Review module
3. generate communication drafts as a completed Communication Assistant module
4. maintain a broad personal knowledge base with topic retrieval and change views

---

## 18. Future Extensions

- autonomous reminder workflows
- calendar-aware planning
- email drafting and triage
- Jira task sync
- Git / PR / incident summarization
- voice input
- mobile-first interaction layer
- multi-agent specialization
- proactive suggestion engine

---

## 19. Engineering Constraints

- prioritize iterative delivery
- prefer modular code organization
- every core flow should have tests
- avoid premature abstraction
- keep the MVP deployable by a single engineer
- log all important agent decisions
- risky external actions require approval

---

## 20. Definition of Done

A feature is done only when:
- code is implemented
- core flow is testable
- basic error handling exists
- docs are updated
- output examples are available
- acceptance criteria are met
