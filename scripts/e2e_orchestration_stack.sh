#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run/e2e"
BACKEND_PORT="${E2E_BACKEND_PORT:-18080}"
FRONTEND_PORT="${E2E_FRONTEND_PORT:-13000}"
DB_PATH="$RUN_DIR/personal_agent_e2e.db"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
TOKEN_FILE="$RUN_DIR/entitlement-token.txt"

APP_ENTITLEMENT_SECRET="${E2E_ENTITLEMENT_SECRET:-personal-agent-e2e-secret}"
export APP_ENTITLEMENT_SECRET
export APP_ENTITLEMENT_REQUIRED=true
export APP_ENABLE_PUBLIC_ENTITLEMENT_BOOTSTRAP=false
export APP_DEFAULT_SUBSCRIPTION_TIER=pro
export APP_RATE_LIMIT_ENABLED=false
export APP_ENVIRONMENT=local
export DATABASE_URL="sqlite:///$DB_PATH"
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:${BACKEND_PORT}/api"

log() {
  echo "[e2e-stack] $*"
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local max_retries=60
  local retry=1

  while (( retry <= max_retries )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      log "$name ready: $url"
      return 0
    fi
    sleep 1
    retry=$((retry + 1))
  done

  log "$name did not become ready: $url"
  log "backend log: $BACKEND_LOG"
  log "frontend log: $FRONTEND_LOG"
  return 1
}

ensure_prerequisites() {
  if [[ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
    log "missing backend virtualenv or uvicorn: backend/.venv/bin/uvicorn"
    log "run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[test]'"
    exit 1
  fi

  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    log "missing frontend/node_modules"
    log "run: cd frontend && npm install"
    exit 1
  fi
}

cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}

mkdir -p "$RUN_DIR"
: > "$BACKEND_LOG"
: > "$FRONTEND_LOG"
rm -f "$DB_PATH" "$TOKEN_FILE"

ensure_prerequisites

log "migrating isolated SQLite database"
(
  cd "$ROOT_DIR/backend"
  ./.venv/bin/alembic upgrade head >/dev/null
  ./.venv/bin/python -m app.db_bootstrap >/dev/null
)

E2E_TOKEN="$(
  cd "$ROOT_DIR/backend"
  ./.venv/bin/python scripts/generate_entitlement.py \
    --tier pro \
    --ttl-seconds 3600 \
    --secret "$APP_ENTITLEMENT_SECRET"
)"
export NEXT_PUBLIC_DEFAULT_ENTITLEMENT_TOKEN="$E2E_TOKEN"
printf "%s" "$E2E_TOKEN" > "$TOKEN_FILE"

PIDS=()
trap cleanup EXIT INT TERM

log "starting backend on :$BACKEND_PORT"
(
  cd "$ROOT_DIR/backend"
  ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" >"$BACKEND_LOG" 2>&1
) &
PIDS+=("$!")

log "starting frontend on :$FRONTEND_PORT"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --hostname 127.0.0.1 --port "$FRONTEND_PORT" >"$FRONTEND_LOG" 2>&1
) &
PIDS+=("$!")

wait_for_http "http://127.0.0.1:${BACKEND_PORT}/health" "backend"
wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" "frontend"

log "stack ready"
while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      wait "$pid"
      exit $?
    fi
  done
  sleep 1
done
