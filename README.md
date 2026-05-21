# Personal Agent Workflow Orchestration MVP

Current product: a deployable DevOps personal workflow orchestration MVP. It focuses on deterministic multi-agent execution, replayable workflow history, queue lifecycle controls, entitlement-aware tier boundaries, and monetization observability.

Long-term vision: a personal AI operating system for work, reflection, knowledge, planning, and communication. The current release keeps that vision grounded in a narrow, auditable orchestration surface that can be deployed and verified by one maintainer.

Monorepo-style app with:
- `frontend/`: Next.js + TypeScript UI
- `backend/`: FastAPI + SQLAlchemy API
- PostgreSQL scaffolding (optional for local via Docker), with SQLite default for fast boot

Documentation map: `docs/README.md`.

## Project Structure

```text
.
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── profile/
│   │   ├── today/
│   │   ├── reflection/
│   │   └── history/
│   └── components/
└── docker-compose.yml
```

## MVP Features

### Current MVP surface
- DevOps-oriented workflow orchestration through Planner, Analyzer, and Reviewer steps.
- Replayable orchestration history backed by persisted step records, not regenerated text.
- Async queue lifecycle with status timeline, retry, and cancel behavior.
- Workflow templates for reusable orchestration step definitions.
- Signed entitlement token support for free/pro/power tier boundaries.
- Monetization observability for capability checks, quota checks, usage events, upgrade blocks, queue health, and KPI aggregation.
- Knowledge and prompt-template utilities that support reuse around orchestration workflows.
- Existing daily plan, reflection, technical analysis, task, and profile routes remain available for compatibility and personal workflow support.

### Data models
- `UserProfile`
- `Task`
- `ReflectionEntry`
- `AgentRunLog`
- `DailyPlan`
- `TechnicalAnalysis`
- `NoteEntry`
- `PromptTemplate`
- `WorkflowOrchestration`
- `WorkflowStepRun`
- `WorkflowTemplate`
- `WorkflowQueueJob`

### APIs
- `POST /api/profile`: create profile
- `PUT /api/profile/{id}`: update profile
- `GET /api/profile/{id}`: get profile
- `POST /api/plans/daily`: submit daily context, generate deterministic plan, persist result
- `GET /api/plans/history`: retrieve saved daily plans
- `POST /api/reflections/daily`: submit reflection inputs, generate deterministic daily summary, persist result
- `GET /api/reflections/history`: retrieve saved structured reflections
- `POST /api/analysis/technical`: submit technical issue context and generate structured analysis
- `GET /api/analysis/history`: retrieve saved technical analyses
- `POST /api/knowledge`: create knowledge entry
- `GET /api/knowledge`: list knowledge entries with optional `q`/`tag` filters
- `GET /api/knowledge/{id}`: get knowledge entry
- `PUT /api/knowledge/{id}`: update knowledge entry
- `DELETE /api/knowledge/{id}`: delete knowledge entry
- `POST /api/templates`: create reusable prompt template
- `GET /api/templates`: list templates with optional `q`/`tag` filters
- `GET /api/templates/init/json`: get built-in template initialization data (JSON)
- `GET /api/templates/init/sql`: get built-in template initialization SQL
- `POST /api/templates/import/json`: import templates via JSON payload or built-in set
- `POST /api/templates/import/sql`: import templates via SQL payload or built-in SQL
- `GET /api/templates/{id}`: get template
- `PUT /api/templates/{id}`: update template
- `DELETE /api/templates/{id}`: delete template
- `POST /api/orchestrations/run`: run deterministic multi-agent orchestration (Planner/Analyzer/Reviewer)
- `GET /api/orchestrations/history`: list orchestration runs with status/tier filters
- `GET /api/orchestrations/{id}`: get orchestration run detail with step replay
- `GET /api/orchestrations/metrics`: orchestration KPI metrics (`days=7|30|...`)
- `POST /api/orchestrations/queue/run`: enqueue orchestration run (async)
- `GET /api/orchestrations/queue/history`: list queue jobs (status/attempts snapshot)
- `GET /api/orchestrations/queue/{job_id}`: get queue job status with real queue events timeline payload
- `POST /api/orchestrations/queue/{job_id}/retry`: retry failed/canceled queue job
- `POST /api/orchestrations/queue/{job_id}/cancel`: request queue job cancellation
- `POST /api/orchestrations/templates`: create orchestration workflow template
- `PUT /api/orchestrations/templates/{id}`: update orchestration workflow template
- `GET /api/orchestrations/templates`: list orchestration workflow templates
- `GET /api/orchestrations/templates/export`: export orchestration workflow templates
- `POST /api/orchestrations/templates/import`: import orchestration workflow templates
- `GET /api/observability/monetization`: monetization observability aggregation (`days=7|30`)
- `GET /api/monetization/profile`: read subscription profile by `subject`
- `GET /api/monetization/usage`: read usage counters by `subject`
- `GET /api/monetization/events`: read newest-first monetization event audit feed
- `POST /api/tasks`: create task
- `GET /api/tasks`: list tasks
- `PUT /api/tasks/{id}`: update task
- `POST /api/reflections`: create reflection
- `GET /api/reflections`: list reflections
- `PUT /api/reflections/{id}`: update reflection

### UI pages
- `/dashboard`
- `/profile`
- `/today`
- `/reflection`
- `/technical-analysis`
- `/orchestrate`
- `/orchestrations`
- `/knowledge`
- `/templates`
- `/history`

## Local Startup

## 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env  # optional
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

### Optional: use PostgreSQL

```bash
docker compose up -d postgres
```

Then set in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/personal_agent
```

Restart backend.

## 2) Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Auto Run For UI Validation

From repo root, one command to start backend + frontend:

```bash
make dev-up
```

Local dev startup runs backend migrations and the same core table bootstrap check used by server deploy before starting `uvicorn`.

Useful companion commands:

```bash
make dev-status   # show running status and URLs
make dev-logs     # stream backend/frontend logs
make dev-down     # stop both services
make dev-restart  # restart both services
```

## Simplified Server Deployment (Recommended MVP Path)

The recommended deploy entry for the current MVP is the Docker Compose server path. It gives one always-on host with PostgreSQL, FastAPI, Next.js, and an Nginx gateway on port `80`:

```bash
DB_PASSWORD='replace-with-strong-password' make server-deploy
```

Backend image build now defaults to:

`PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`

You can still override it when needed:

```bash
PIP_INDEX_URL='https://pypi.tuna.tsinghua.edu.cn/simple' \
DB_PASSWORD='replace-with-strong-password' \
make server-deploy
```

If backend keeps restarting after password/env changes, reset old Postgres data volume once:

```bash
DB_PASSWORD='replace-with-strong-password' RESET_DB=1 make server-deploy
```

If your DB password contains special URL characters (for example `@`, `#`, `:`), either keep using `make server-deploy` (it now auto-encodes for backend DSN), or set explicitly:

```bash
DB_PASSWORD='raw-password' DB_PASSWORD_URLENC='url-encoded-password' make server-deploy
```

This starts:
- `postgres`
- `backend`
- `frontend`
- `gateway` (Nginx on port `80`, routing `/api` to backend)

Server startup now runs: `alembic upgrade head -> core table bootstrap check -> uvicorn`.
This protects against partial migration states that can cause missing-table runtime errors.

## Entitlement Gate (Billing-ready tier check)

Orchestration APIs now support signed entitlement token:

- header: `X-Entitlement: <signed_token>`
- env:
  - `APP_ENVIRONMENT=local|staging|production`
  - `APP_ENTITLEMENT_REQUIRED=true|false`
  - `APP_ENTITLEMENT_SECRET=<strong-secret>`
  - `APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK=true|false` (non-production only)

Effective auth behavior:

- In `production`, signed `X-Entitlement` is always required and `X-Subscription-Tier` fallback is disabled.
- In non-production, `X-Subscription-Tier` fallback is only honored when `APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK=true`.
- `APP_ENTITLEMENT_REQUIRED=true` enforces signed `X-Entitlement` in every environment.
- Signed token is authoritative when both headers are provided (`X-Entitlement` tier overrides mismatched legacy tier header).
- Expired or signature-invalid tokens return deterministic `401` errors.
- Free tier capability guard denies multi-step orchestration runs with `403`.
- The `/orchestrate` frontend uses signed entitlement tokens and no longer emits `X-Subscription-Tier`; the legacy header remains an explicit non-production API fallback only.

Observability and quota contract notes:

- `GET /api/orchestrations/metrics` response fields are stable and ordered as:
  `period_days`, `total_runs`, `weekly_active_orchestrations`, `partial_success_rate`, `average_duration_ms`.
- `GET /api/orchestrations/history` is returned newest-first for deterministic dashboard aggregation.
- Global request quota/rate-limit boundary returns `429 Too many requests. Please retry later.` once configured per window limit is exceeded.
- Dashboard contract note: monetization observability backend route is `GET /api/observability/monetization`; the frontend API client uses this canonical route.

Generate a local token for testing:

```bash
make entitlement-token TIER=pro TTL_SECONDS=3600
```

Use the generated token in `/orchestrate` page (Entitlement Token field), or pass it via header in API calls.

Useful operations:

```bash
make server-status
make server-logs
make server-restart
make server-down
```

Detailed guide: `docs/deploy-simple-server.md`.

### Deployment Verification

After `make server-deploy`, verify the deployment through the gateway:

```bash
make server-status
curl http://<server-host>/api/health
```

Then open the user-facing orchestration surfaces:

- `http://<server-host>/orchestrate`
- `http://<server-host>/orchestrations`
- `http://<server-host>/dashboard`

For API-level validation, run a signed pro/power orchestration request or use the entitlement token field on `/orchestrate`. Free tier should still reject multi-step orchestration with a deterministic `403`.

### Public Access Paths

After `make server-deploy`, public routes are served by the gateway. Replace `<server-host>` with the server IP or domain:

- Home: `http://<server-host>/`
- Dashboard: `http://<server-host>/dashboard`
- Today Plan: `http://<server-host>/today`
- Reflection: `http://<server-host>/reflection`
- Technical Analysis: `http://<server-host>/technical-analysis`
- Orchestrate: `http://<server-host>/orchestrate`
- Orchestration History: `http://<server-host>/orchestrations`
- Knowledge: `http://<server-host>/knowledge`
- Templates: `http://<server-host>/templates`
- API health: `http://<server-host>/api/health`

If you deploy with `DOMAIN=<server-ip>.nip.io`, equivalent paths are:

- `http://<server-ip>.nip.io/`
- `http://<server-ip>.nip.io/dashboard`
- `http://<server-ip>.nip.io/api/health`

## Migration Commands

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
```

## Tests

Run backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

Current test coverage includes:
- app startup
- `/health` endpoint
- daily planning generation + persistence + history retrieval
- daily reflection summary generation + persistence + history retrieval
- technical analysis generation + request validation + persistence + history retrieval
- smoke-check script coverage for UI routes and core APIs, including orchestration run/history/metrics, queue run/history, monetization observability, and monetization read APIs
- orchestration workflow run + step replay + partial failure fallback + history retrieval
- free/pro/power tier boundary for orchestration (free single-step restriction)
- orchestration template CRUD + import/export round-trip
- knowledge entry CRUD + filtering + ordering/validation edge cases
- prompt template CRUD + filtering
- prompt template batch import (JSON/SQL) and built-in starter library
- dashboard/history frontend failure fallback and sanitized error messaging

Run frontend tests:

```bash
cd frontend
npm test
```

Run full-stack tests in one command (repo root):

```bash
make test
```

Run parallel quality checks (repo root):

```bash
# backend tests + frontend tests + frontend build (parallel)
make qa-fast

# visual baseline snapshots (dashboard, knowledge)
make qa-visual

# full quality chain
make qa-all

# app smoke checks (routes + core API loops)
make smoke-check
```

Release preflight gate:

```bash
make release-check
```

This runs `qa-all` and `k8s-dry-run` as a single pre-release check.

Containerized K8s deployment options:

```bash
# Kind-based online deployment
make kind-deploy

# K3d-based online deployment (recommended fallback for older kernels)
make k3d-deploy
```

Continuous iteration modes (repo root):

```bash
# keep running forever, every 10s
make test-watch

# retry until all tests pass, then stop
make test-until-pass
```

CI is configured in `.github/workflows/ci.yml` with parallel jobs:

- `backend-test`
- `frontend-test`
- `frontend-build`
- `visual-baseline`
- `integration-gate` (depends on all jobs above)

Design/motion reuse guidance is documented in `docs/visual-guidelines.md`.
Release gate checklist is documented in `docs/release-checklist.md`.
K3d online deployment guide is documented in `docs/deploy-k3d-online.md`.

## Template Initialization Import

You can bootstrap reusable prompt templates in either format:

```bash
# JSON import using built-in starter library
curl -X POST http://localhost:8000/api/templates/import/json \
  -H "Content-Type: application/json" \
  -d '{"use_builtin": true, "upsert_by_name": true}'

# SQL import using built-in starter SQL
curl -X POST http://localhost:8000/api/templates/import/sql \
  -H "Content-Type: application/json" \
  -d '{"use_builtin": true, "reset_existing": false}'
```

Or run local helper commands from repo root:

```bash
make templates-import-json
make templates-import-sql
```

## Current Limitations

This MVP intentionally keeps scope small. Current constraints:

- No semantic/vector search or ranking for knowledge retrieval yet.
- Knowledge and templates support only basic text query (`q`) and exact tag filter (`tag`) in backend retrieval.
- No RBAC / multi-tenant separation in app layer yet.
- Orchestration has a lightweight FastAPI background-task queue, but no separate durable worker process yet.
- Technical analysis output is deterministic rules-based (inspectable), not model-generated ranking.
- Communication assistant and Weekly Review are roadmap capabilities only; there are no current production UI pages or APIs for those workflows.
- Kubernetes manifests are baseline production-ready for a single environment, but remain non-HA.
- This release still avoids external integrations and autonomous external actions.

## Security Hardening (Current)

- API basic rate limiting is enabled by default for `/api/*` requests.
  - Env knobs: `APP_RATE_LIMIT_ENABLED`, `APP_RATE_LIMIT_MAX_REQUESTS`, `APP_RATE_LIMIT_WINDOW_SECONDS`.
- Agent run logs are sanitized for sensitive values (`password`, `token`, `secret`, bearer tokens) before persistence.
- Core workflow inputs enforce maximum payload size/line-item bounds to reduce abuse risk and storage pressure.

## Kubernetes Deployment (First Version)

### 1) Build and push images

```bash
# repo root
docker build -f backend/Dockerfile -t ghcr.io/your-org/personal-agent-backend:latest .
docker build -f frontend/Dockerfile -t ghcr.io/your-org/personal-agent-frontend:latest .

docker push ghcr.io/your-org/personal-agent-backend:latest
docker push ghcr.io/your-org/personal-agent-frontend:latest
```

Update image addresses in:
- `k8s/backend.yaml`
- `k8s/frontend.yaml`

### 2) Configure PostgreSQL secret

```bash
cp k8s/postgres-secret.example.yaml /tmp/postgres-secret.yaml
# edit POSTGRES_PASSWORD in /tmp/postgres-secret.yaml
kubectl apply -f /tmp/postgres-secret.yaml
```

Important: update `DATABASE_URL` password in `k8s/backend.yaml` (`backend-secret`) to match.

### 3) Dry-run validation

```bash
make k8s-dry-run
```

### 4) Apply resources

```bash
make k8s-apply
```

### 5) Verify rollout

```bash
make k8s-verify
```

K8s resources are under `k8s/`:
- namespace, postgres statefulset/service, backend, frontend, ingress

Detailed guide:
- `docs/k8s-deploy.md`
