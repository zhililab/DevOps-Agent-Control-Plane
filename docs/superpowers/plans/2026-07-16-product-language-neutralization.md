# Product Language Neutralization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove career-preparation framing from the product surface, repository, persisted Pilot identity, and commit metadata while keeping Agent Quality Lab behavior unchanged.

**Architecture:** A repository guard scans tracked content and commit messages for disallowed vocabulary. Product copy and fixtures use customer-facing quality and operational evidence language, while an idempotent Alembic migration normalizes the previously stored Pilot subject.

**Tech Stack:** Bash, Git, Next.js/React/TypeScript, FastAPI/Python, Alembic, PostgreSQL, Playwright.

## Global Constraints

- Preserve Agent Quality Lab APIs, evaluation metrics, deterministic policy authority, and production Provider evidence.
- Do not expose or rotate Provider or evaluation-write credentials during this language-only change.
- Keep production deployment on Docker Compose with `RESET_DB=0`.
- Existing Git history is rewritten only if commit-message audit finds a match.

---

### Task 1: Add Product Language Guard

**Files:**
- Create: `scripts/product_language_check.sh`
- Modify: `Makefile`

- [ ] Add a tracked-content and commit-message scanner whose source does not contain the assembled disallowed vocabulary.
- [ ] Run it against the current tree and confirm it fails on existing product copy.
- [ ] Add `product-language-check` to `release-check`.

### Task 2: Neutralize Product And Test Language

**Files:**
- Modify: `frontend/features/evaluation/QualityLabView.tsx`
- Modify: `backend/tests/test_agent_quality_evaluation.py`
- Modify: `README.md`
- Modify: `PLANS.MD`
- Modify: `PLANS.html`
- Modify: `docs/core-functionality-check.md`
- Modify: `docs/mvp-demo-runbook.md`
- Modify: `docs/deployment-evidence.md`

- [ ] Replace career-preparation framing with quality evidence, operational evidence, customer proof, and neutral reviewer/subject identifiers.
- [ ] Run the guard and confirm tracked content plus commit messages pass.
- [ ] Run focused frontend and backend tests.

### Task 3: Normalize Persisted Pilot Identity

**Files:**
- Create: `backend/alembic/versions/0019_normalize_quality_evidence_subject.py`
- Modify: `backend/tests/test_db_bootstrap.py`

- [ ] Add an idempotent migration that changes the legacy Pilot subject to `quality-evidence` without embedding disallowed vocabulary as a contiguous source string.
- [ ] Verify an empty database upgrades to the new head.
- [ ] Deploy with `RESET_DB=0` and verify production data contains no residual match.

### Task 4: Verify And Release

**Files:**
- Modify: `docs/deployment-evidence.md`

- [ ] Run `make release-check` and the production runtime security/smoke checks.
- [ ] Commit with customer-facing product language and push `master`.
- [ ] Deploy, verify `/evaluation` copy, query persisted data, and re-audit Git commit messages.
