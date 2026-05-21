# Deployment Evidence

This file records the current MVP deployment evidence for the Docker Compose server path.

## 2026-05-21 Server Release

- Release path: Docker Compose server deployment through `make server-deploy`.
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- App directory on server: `/root/code/personal-agent-ws/personal-agent`
- Deployed commit: `1e005db chore: release deploy 2026-05-21-2255`
- Follow-up docs/script commit: `eb32a17 docs: align deployment health check path`
- Verified public routes:
  - `http://1.117.63.81/dashboard`
  - `http://1.117.63.81/orchestrate`
  - `http://1.117.63.81/orchestrations`

## Verification Results

- Local gate before release: `make qa-fast` passed.
- Remote deployment command completed through `make server-deploy`.
- Remote smoke checks passed for:
  - frontend routes
  - backend `/health`
  - daily plan, reflection, and technical analysis APIs
  - orchestration run, history, metrics, and queue APIs
  - monetization observability and read APIs
  - knowledge and template listing response shape
- Public post-deploy checks:
  - `curl http://1.117.63.81/health` returned `{"status":"ok"}`
  - `http://1.117.63.81/dashboard` returned `200`

## 2026-05-21 Security Hardening Baseline

- Added planned checks:
  - `make security-check`
  - gateway security headers
  - report-only CSP
  - production CORS origin configuration
  - frontend dependency high/critical audit
  - runtime entitlement, free-tier, canonical health, and oversized-payload assertions
- Expected deployment behavior:
  - remote `make server-deploy` runs smoke checks and runtime security checks
  - deployment uses `RESET_DB=0` unless the database can be discarded

## 2026-05-22 Hardening Release Verification

- Latest deployed commit: `96902f9 chore: release deploy 2026-05-22-0016`
- Server: `http://1.117.63.81`
- Health: `http://1.117.63.81/health`
- Release path: `make release-deploy` -> remote `make server-deploy`
- Database reset: `RESET_DB=0`
- Release fixes included:
  - deterministic startup migration wrapper for legacy bootstrap-created databases
  - direct Alembic head marker recovery for existing schemas without `alembic_version`
  - forced gateway recreation during server deploy so mounted Nginx config changes take effect
  - gateway hiding of upstream `X-Powered-By`
- Verified on remote:
  - gateway and backend readiness checks passed
  - smoke checks passed for core pages and core workflow APIs
  - runtime security check passed for security headers, canonical health, entitlement boundary, oversized payload handling, and no exposed `X-Powered-By`

## Operational Notes

- The current release path is the Docker Compose server path, not k3d/k8s.
- k3d/k8s manifests remain useful for follow-up deployment validation.
- `REMOTE_RESET_DB=1` must only be used when the remote database can be discarded.
- Routine docs/script updates should sync the repository without running a destructive reset deployment.
