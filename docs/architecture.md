# MVP Architecture Notes

## Backend
- FastAPI app with modular routers: `profile`, `plan`, `summary`, `history`
- SQLAlchemy models for core entities
- Service layer for planning, summary generation, and agent action logging
- DB configurable by `DATABASE_URL` (SQLite default, PostgreSQL ready)

## Frontend
- Next.js app router pages for MVP flow
- Thin API client in `frontend/lib/api.ts`
- Client-side forms to invoke backend APIs and display results

## Auditability
- `AgentRunLog` records each plan/summary generation request and concise output metadata
