# Release Checklist (MVP)

This checklist standardizes pre-release verification for the current Docker Compose server-path MVP.

## 1) Local Quality Gate

Run from repo root:

```bash
make qa-all
```

Expected:
- backend tests pass
- frontend tests pass
- frontend production build passes
- visual baseline tests pass

## 2) Browser E2E Gate

Run the real-browser orchestration flow:

```bash
make e2e-orchestration
```

Expected:
- `/orchestrate` submits a signed entitlement orchestration run
- run replay is visible after submission
- `/orchestrations` shows the created run and persisted step replay
- browser request includes `X-Entitlement` and does not emit legacy `X-Subscription-Tier`

## 3) Manifest Render Gate

Render Kubernetes manifests without requiring a reachable cluster:

```bash
make k8s-render
```

Expected:
- manifests render successfully for later k3d/k8s validation

## 4) Server Deploy Gate

Deploy through the current MVP server path:

```bash
make release-deploy
```

Expected:
- local configured gate passes before commit/push
- remote host pulls `origin/master`
- `make server-deploy` completes on the server
- remote smoke checks pass

Set `REMOTE_RESET_DB=1` only when the remote database can be discarded. Routine docs/script changes should keep it at `0`.

## 5) Runtime Verification Gate

Verify the deployed gateway:

```bash
curl http://1.117.63.81/health
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/dashboard
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/orchestrate
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/orchestrations
```

Expected:
- health returns `{"status":"ok"}`
- core pages return `200`

## 6) Smoke Check Gate

Automated smoke check:

```bash
make smoke-check
```

This command verifies:
- frontend routes (`/dashboard`, `/today`, `/reflection`, `/technical-analysis`, `/orchestrate`, `/orchestrations`, `/knowledge`, `/templates`)
- backend health (`/health`)
- core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, and monetization read APIs

## 7) Rollback Trigger

Rollback should be considered if any of these happen:
- repeated 5xx in backend logs after rollout
- frontend page crashes on main workflows
- persistent DB migration or connectivity failure

Current limitation reminder:
- single environment, no HA, and no multi-tenant isolation.
- k3d/k8s deployment verification is retained as a follow-up path and does not block the current Docker Compose server release.
