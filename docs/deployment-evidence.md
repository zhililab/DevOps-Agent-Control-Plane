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

## Operational Notes

- The current release path is the Docker Compose server path, not k3d/k8s.
- k3d/k8s manifests remain useful for follow-up deployment validation.
- `REMOTE_RESET_DB=1` must only be used when the remote database can be discarded.
- Routine docs/script updates should sync the repository without running a destructive reset deployment.
