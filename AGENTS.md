# AGENTS.md

## Project Purpose
Build a personal AI agent assistant focused on execution, reflection, and reusable workflows.

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

## Security Baseline
- Keep sensitive input (tokens, passwords, secrets) out of plain logs.
- Add guardrails for oversized payloads and abusive request patterns.
- Prefer deterministic validation errors over silent truncation in user-facing APIs.
- Keep externally exposed deployment paths minimal and easy to audit.

## Task Expectations
When given a task:
1. understand the goal
2. identify impacted modules
3. propose a short plan
4. implement incrementally
5. run relevant tests
6. update docs if behavior changes
7. confirm with the user if the task is completed

## Do Not
- do not introduce unrelated refactors
- do not silently change architecture without documenting it
- do not skip tests for core flows
- do not perform risky external actions without approval

## Definition of Done
A task is done when:
- implementation is complete
- tests pass
- key edge cases are handled
- docs are updated if needed
- output can be manually verified
