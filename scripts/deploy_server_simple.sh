#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PASSWORD="${DB_PASSWORD:-}"
PUBLIC_HOST="${PUBLIC_HOST:-}"
RESET_DB="${RESET_DB:-0}"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "[deploy-simple] missing DB_PASSWORD env"
  echo "Example: DB_PASSWORD='strong-password' make server-deploy"
  exit 2
fi

if [[ -z "$PUBLIC_HOST" ]]; then
  PUBLIC_HOST="$(curl -4 -fsS ifconfig.me 2>/dev/null || true)"
  if [[ -z "$PUBLIC_HOST" ]]; then
    PUBLIC_HOST="127.0.0.1"
  fi
fi

log() {
  echo "[deploy-simple] $*"
}

print_diag() {
  log "docker compose status"
  docker compose -f docker-compose.server.yml ps || true
  log "recent backend logs"
  docker logs --tail 120 personal-agent-backend 2>/dev/null || true
  log "recent postgres logs"
  docker logs --tail 120 personal-agent-postgres 2>/dev/null || true
  log "recent gateway logs"
  docker logs --tail 80 personal-agent-gateway 2>/dev/null || true
}

wait_http() {
  local url="$1"
  local name="$2"
  local max_retries=60
  local i=1
  while (( i <= max_retries )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name ready: $url"
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done
  log "$name not ready in time: $url"
  return 1
}

cd "$ROOT_DIR"

if [[ "$RESET_DB" == "1" ]]; then
  log "RESET_DB=1 -> removing existing stack and postgres volume"
  docker compose -f docker-compose.server.yml down -v || true
fi

log "starting stack with docker compose"
DB_PASSWORD="$DB_PASSWORD" docker compose -f docker-compose.server.yml up -d --build

wait_http "http://127.0.0.1/" "gateway"
if ! wait_http "http://127.0.0.1/health" "backend"; then
  print_diag
  log "hint: if DB password changed while reusing old volume, rerun with RESET_DB=1"
  log "hint: example -> DB_PASSWORD='your-password' RESET_DB=1 make server-deploy"
  exit 1
fi

log "running smoke-check against gateway/backend"
FRONTEND_BASE="http://127.0.0.1" BACKEND_BASE="http://127.0.0.1" ./scripts/smoke_check.sh

log "deployment completed"
log "open: http://${PUBLIC_HOST}"
log "api:  http://${PUBLIC_HOST}/api/health"
