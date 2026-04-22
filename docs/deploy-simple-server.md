# Simple Server Deployment (Recommended MVP Path)

This is the easiest always-on deployment path without Kubernetes.

Architecture:
- `postgres` (data)
- `backend` (FastAPI)
- `frontend` (Next.js)
- `gateway` (Nginx on port 80, routes `/api` to backend)

## 1) Prerequisites

- Docker + Docker Compose plugin installed
- Server security group allows port `80`
- Public IP available (or domain bound to the server)

## 2) One-command deploy

```bash
cd /path/to/personal-agent
DB_PASSWORD='replace-with-strong-password' make server-deploy
```

## 3) Access

- Home: `http://<server-public-ip>/`
- API health: `http://<server-public-ip>/api/health`

## 4) Operations

```bash
# status/logs
make server-status
make server-logs

# restart / stop
make server-restart
make server-down
```

Data persistence:
- PostgreSQL data is stored in docker volume `pgdata`.
