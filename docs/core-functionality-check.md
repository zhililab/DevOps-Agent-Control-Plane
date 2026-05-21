# Core Functionality Check

This document records the current product target and the minimum functionality that must stay green for the DevOps orchestration MVP.

## Current Product Target

- Current release target: deterministic DevOps personal workflow orchestration MVP.
- Primary surfaces: `/orchestrate`, `/orchestrations`, and `/dashboard`.
- Release path: Docker Compose server deployment through `make release-deploy`.
- Public entrypoint: `http://1.117.63.81`.
- Canonical health route: `/health`.

## Core User Flows

- Run a sync orchestration from `/orchestrate` with a signed entitlement token.
- Inspect run replay immediately after the orchestration finishes.
- Navigate to `/orchestrations` and verify persisted run history and step replay.
- Submit queued orchestration work, then inspect queue job state, retry/cancel controls, and timeline replay.
- Review dashboard orchestration KPIs and monetization observability fallback states.
- Generate and persist daily plans, daily reflections, and technical analysis records.
- Browse reusable knowledge entries, prompt templates, and workflow templates.

## Core API Surface

- `GET /health`
- `POST /api/plans/daily`
- `POST /api/reflections/daily`
- `POST /api/analysis/technical`
- `POST /api/orchestrations/run`
- `GET /api/orchestrations/history`
- `GET /api/orchestrations/{id}`
- `GET /api/orchestrations/metrics?days=...`
- `POST /api/orchestrations/queue/run`
- `GET /api/orchestrations/queue/history`
- `GET /api/orchestrations/queue/{job_id}`
- `POST /api/orchestrations/queue/{job_id}/retry`
- `POST /api/orchestrations/queue/{job_id}/cancel`
- `GET /api/observability/monetization?days=...`
- `GET /api/monetization/profile|usage|events`

## Security And Robustness Baseline

- Production orchestration actions require signed `X-Entitlement`.
- Legacy `X-Subscription-Tier` is disabled in production.
- Free tier must reject multi-step orchestration with `403`.
- Missing entitlement must reject orchestration with `401`.
- Oversized structured payloads must reject with `422` or gateway `413`.
- API rate limit must return `429` with `Retry-After`.
- Gateway responses must include baseline security headers.
- `X-Powered-By` must not be exposed by the frontend.
- `/api/health` must not become a second health route; `/health` remains canonical.

## Non-Blocking Product Modules

- P7 Communication Assistant remains part of the long-term personal assistant vision.
- P8 Weekly Review remains planned, but is not a blocker for the current orchestration MVP.
- k3d/k8s deployment verification remains a follow-up deployment path, not the current release blocker.
