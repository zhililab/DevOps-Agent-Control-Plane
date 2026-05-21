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
- `/orchestrations` can verify the run history ledger and show valid integrity status
- browser request includes `X-Entitlement` and does not emit legacy `X-Subscription-Tier`

## 3) Security Gate

Run the security and robustness checks:

```bash
make security-check
```

Expected:
- gateway security headers are present in config
- frontend does not expose `X-Powered-By`
- backend security tests pass for CORS, rate limiting, payload bounds, and log sanitization
- frontend dependency audit has no high or critical vulnerabilities
- runtime gateway assertions run when `SECURITY_CHECK_BASE` is provided

## 4) Manifest Render Gate

Render Kubernetes manifests without requiring a reachable cluster:

```bash
make k8s-render
```

Expected:
- manifests render successfully for later k3d/k8s validation

## 5) Server Deploy Gate

Deploy through the current MVP server path:

```bash
# required before history/data migrations
ssh -x root@1.117.63.81 'cd /root/code/personal-agent-ws/personal-agent && mkdir -p deploy/backups && docker exec personal-agent-postgres pg_dump -U postgres personal_agent > deploy/backups/personal_agent-$(date +%Y%m%d-%H%M%S).sql'
make release-deploy
```

Expected:
- database backup is captured before migrations that alter historical data
- local configured gate passes before commit/push
- remote host pulls `origin/master`
- `make server-deploy` completes on the server
- remote smoke checks pass
- remote runtime security checks pass

Set `REMOTE_RESET_DB=1` only when the remote database can be discarded. Routine docs/script changes should keep it at `0`.

## 6) Runtime Verification Gate

Verify the deployed gateway:

```bash
curl http://1.117.63.81/health
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/dashboard
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/orchestrate
curl -s -o /dev/null -w '%{http_code}' http://1.117.63.81/orchestrations
curl -s http://1.117.63.81/api/plans/history
curl -s 'http://1.117.63.81/api/plans/history?include_system=true'
```

Expected:
- health returns `{"status":"ok"}`
- core pages return `200`
- core page responses include baseline security headers
- `X-Powered-By` is not exposed
- default personal history excludes smoke/system records
- `include_system=true` exposes tagged smoke/system records for audit

## 7) Smoke Check Gate

Automated smoke check:

```bash
make smoke-check
```

This command verifies:
- frontend routes (`/dashboard`, `/today`, `/reflection`, `/technical-analysis`, `/orchestrate`, `/orchestrations`, `/knowledge`, `/templates`)
- backend health (`/health`)
- core workflow APIs, orchestration run/history/metrics, queue run/history, monetization observability, and monetization read APIs
- history ledger integrity and idempotent backfill tests are covered by the local release gate
- smoke-created daily/reflection/analysis records are tagged with `X-Record-Source: smoke_check`

## 8) Rollback Trigger

Rollback should be considered if any of these happen:
- repeated 5xx in backend logs after rollout
- frontend page crashes on main workflows
- persistent DB migration or connectivity failure

Current limitation reminder:
- single environment, no HA, and no multi-tenant isolation.
- k3d/k8s deployment verification is retained as a follow-up path and does not block the current Docker Compose server release.
