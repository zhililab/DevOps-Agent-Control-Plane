# Release Checklist (MVP)

This checklist standardizes pre-release verification for the current single-environment MVP.

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

## 2) Kubernetes Manifest Gate

Dry-run manifests before apply:

```bash
make k8s-dry-run
```

Expected:
- no validation/apply errors in client dry-run

## 3) Deploy Gate

Apply manifests:

```bash
make k8s-apply
```

## 4) Runtime Verification Gate

Verify rollout and logs:

```bash
make k8s-verify
```

Expected:
- backend/frontend rollout successful
- pods/services/ingress visible
- no critical errors in backend/frontend tail logs

## 5) Smoke Check Gate

Automated local smoke check:

```bash
make smoke-check
```

This command verifies:
- frontend routes (`/dashboard`, `/today`, `/reflection`, `/technical-analysis`, `/knowledge`, `/templates`)
- backend health (`/health`)
- core workflow APIs (`/api/plans/daily`, `/api/reflections/daily`, `/api/analysis/technical`)

## 6) Rollback Trigger

Rollback should be considered if any of these happen:
- repeated 5xx in backend logs after rollout
- frontend page crashes on main workflows
- persistent DB migration or connectivity failure

Current limitation reminder:
- single environment, no HA, no queue workers, no multi-tenant isolation.
