# Kubernetes Deployment Guide (First Version)

This document provides a minimal production deployment path for this MVP.

## What This Includes

- Namespace, PostgreSQL StatefulSet, backend Deployment, frontend Deployment
- Services and Ingress routing (`/api` -> backend, `/` -> frontend)
- Baseline startup/readiness/liveness probes and migration-on-start for backend
- Baseline resource requests/limits and rolling update strategy for backend/frontend

## Current Constraints

- Single-replica backend/frontend by default.
- PostgreSQL is a single StatefulSet instance (no HA/failover).
- Secrets are plain Kubernetes Secrets (no external secret manager integration yet).
- No autoscaling, service mesh, or zero-downtime migration orchestration yet.
- No queue workers/background jobs for heavy tasks yet.
- No multi-tenant isolation or RBAC in app layer yet.

## Prerequisites

- Kubernetes cluster reachable by current `kubectl` context
- Ingress controller (for example NGINX Ingress)
- Image registry access for backend/frontend images

## Build and Push Images

```bash
docker build -f backend/Dockerfile -t ghcr.io/your-org/personal-agent-backend:latest .
docker build -f frontend/Dockerfile -t ghcr.io/your-org/personal-agent-frontend:latest .

docker push ghcr.io/your-org/personal-agent-backend:latest
docker push ghcr.io/your-org/personal-agent-frontend:latest
```

Update image addresses in:

- `k8s/backend.yaml`
- `k8s/frontend.yaml`

## Configure Secrets

1. Copy and edit PostgreSQL secret:

```bash
cp k8s/postgres-secret.example.yaml /tmp/postgres-secret.yaml
```

2. Set a strong password in `/tmp/postgres-secret.yaml`.
3. Keep `k8s/backend.yaml` `DATABASE_URL` password aligned with PostgreSQL password.

Apply PostgreSQL secret:

```bash
kubectl apply -f /tmp/postgres-secret.yaml
```

## Deploy

Render manifests:

```bash
./scripts/k8s_deploy.sh render
```

Dry-run first:

```bash
make k8s-dry-run
```

Then apply manifests:

```bash
./scripts/k8s_deploy.sh apply
```

Or:

```bash
make k8s-apply
```

## Verify

```bash
./scripts/k8s_deploy.sh verify
```

Or:

```bash
make k8s-verify
```
