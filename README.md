# Personal Agent Assistant MVP

Monorepo-style MVP with:
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
- `POST /api/orchestrations/templates`: create orchestration workflow template
- `PUT /api/orchestrations/templates/{id}`: update orchestration workflow template
- `GET /api/orchestrations/templates`: list orchestration workflow templates
- `GET /api/orchestrations/templates/export`: export orchestration workflow templates
- `POST /api/orchestrations/templates/import`: import orchestration workflow templates
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

Useful companion commands:

```bash
make dev-status   # show running status and URLs
make dev-logs     # stream backend/frontend logs
make dev-down     # stop both services
make dev-restart  # restart both services
```

## Simplified Server Deployment (Recommended)

For quickest always-on access on a server (without Kubernetes), use Docker Compose:

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

Useful operations:

```bash
make server-status
make server-logs
make server-restart
make server-down
```

Detailed guide: `docs/deploy-simple-server.md`.

### Public Access Paths

After `make server-deploy`, public routes are:

- Home: `http://1.117.63.81/`
- Dashboard: `http://1.117.63.81/dashboard`
- Today Plan: `http://1.117.63.81/today`
- Reflection: `http://1.117.63.81/reflection`
- Technical Analysis: `http://1.117.63.81/technical-analysis`
- Knowledge: `http://1.117.63.81/knowledge`
- Templates: `http://1.117.63.81/templates`
- API health: `http://1.117.63.81/api/health`

If you deploy with `DOMAIN=1.117.63.81.nip.io`, equivalent paths are:

- `http://1.117.63.81.nip.io/`
- `http://1.117.63.81.nip.io/dashboard`
- `http://1.117.63.81.nip.io/api/health`

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
- No background jobs / queue for heavy analysis requests.
- Technical analysis output is deterministic rules-based (inspectable), not model-generated ranking.
- Kubernetes manifests are baseline production-ready for a single environment, but remain non-HA.
- This release still avoids external integrations and async orchestration.

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
