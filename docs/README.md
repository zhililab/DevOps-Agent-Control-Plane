# Documentation Map

This directory keeps project documents that explain how the personal agent is designed, operated, released, and evolved.

## Start Here

- `../README.md`: project overview, local startup, APIs, tests, and deployment commands.
- `../specs.md`: product vision, MVP scope, functional requirements, data model, and acceptance criteria.
- `../AGENTS.md`: working rules for coding agents in this repository.

## Product And Architecture

- `architecture.md`: compact MVP architecture notes for backend, frontend, and audit logging.
- `core-functionality-check.md`: current MVP target, core pages/APIs, release path, and security baseline.
- `visual-guidelines.md`: UI theme tokens, reusable component rules, motion guidance, and accessibility guardrails.

## Deployment

Use the simplest path that fits the target environment:

- `deploy-simple-server.md`: recommended MVP deployment path using Docker Compose and Nginx gateway.
- `deploy-k3d-online.md`: Kubernetes-on-Docker path for servers where Kind is blocked by old kernel capabilities.
- `deploy-kind-online.md`: Kind-based single-server Kubernetes deployment.
- `k8s-deploy.md`: generic Kubernetes deployment guide for an existing cluster and image registry.
- `deployment-evidence.md`: current server release evidence, public routes, commits, and smoke-check status.

## Release

- `release-checklist.md`: local quality gates, browser E2E, server deployment verification, smoke checks, and rollback triggers.

## Current Organization Notes

- `README.md` currently acts as the operational entry point and includes some deployment details repeated in `docs/`.
- `specs.md` is the product source of truth and should stay higher-level than implementation docs.
- Deployment docs are intentionally split by environment so risky production steps stay easy to audit.

## Suggested Maintenance Rules

- Update `README.md` when commands or first-run behavior changes.
- Update `specs.md` when product scope, acceptance criteria, or core user scenarios change.
- Update `architecture.md` when module boundaries, persistence, or orchestration flows change.
- Update deployment docs when scripts, environment variables, ports, manifests, or rollback behavior change.
- Update `release-checklist.md` whenever the quality gate changes.
