#!/usr/bin/env bash

set -euo pipefail

FRONTEND_BASE="${FRONTEND_BASE:-http://127.0.0.1:3000}"
BACKEND_BASE="${BACKEND_BASE:-http://127.0.0.1:8000}"
API_BASE="${API_BASE:-$BACKEND_BASE/api}"

log() {
  echo "[smoke] $*"
}

fetch_status() {
  local url="$1"
  local status
  status="$(curl -sS -o /tmp/personal-agent-smoke-body.txt -w "%{http_code}" "$url" || true)"
  if [[ -z "$status" || "$status" == "000" ]]; then
    echo "000"
    return
  fi
  echo "$status"
}

assert_route_ok() {
  local path="$1"
  local status
  status="$(fetch_status "${FRONTEND_BASE}${path}")"
  if [[ "$status" != "200" ]]; then
    log "route failed: ${path} (status=${status})"
    cat /tmp/personal-agent-smoke-body.txt
    return 1
  fi
  log "route ok: ${path}"
}

assert_api_json_contains() {
  local url="$1"
  local payload="$2"
  local must_contain="$3"

  local body
  body="$(curl -sS -X POST "$url" -H "Content-Type: application/json" -d "$payload")"

  if [[ "$body" != *"$must_contain"* ]]; then
    log "api assertion failed: ${url} missing '${must_contain}'"
    echo "$body"
    return 1
  fi

  log "api ok: ${url} contains '${must_contain}'"
}

assert_api_get_is_array() {
  local url="$1"
  local body
  body="$(curl -sS "$url")"

  if ! printf "%s" "$body" | grep -Eq '^[[:space:]]*\['; then
    log "api assertion failed: ${url} is not a JSON array response"
    echo "$body"
    return 1
  fi

  log "api ok: ${url} returns JSON array"
}

main() {
  : > /tmp/personal-agent-smoke-body.txt
  log "checking frontend routes"
  assert_route_ok "/dashboard"
  assert_route_ok "/today"
  assert_route_ok "/reflection"
  assert_route_ok "/technical-analysis"
  assert_route_ok "/knowledge"
  assert_route_ok "/templates"

  log "checking backend health"
  local health_status
  health_status="$(fetch_status "${BACKEND_BASE}/health")"
  if [[ "$health_status" != "200" ]]; then
    log "backend health failed (status=${health_status})"
    cat /tmp/personal-agent-smoke-body.txt
    return 1
  fi
  log "backend health ok"

  log "checking core API workflows"
  assert_api_json_contains \
    "${API_BASE}/plans/daily" \
    '{"tasks":["Smoke task"],"meetings":["Smoke meeting"],"blockers":["None"],"priorities":["Smoke task"]}' \
    '"status_summary"'

  assert_api_json_contains \
    "${API_BASE}/reflections/daily" \
    '{"completed":["Done"],"unfinished":["Todo"],"blockers":["Dependency"],"mood_or_notes":"steady"}' \
    '"day_summary"'

  assert_api_json_contains \
    "${API_BASE}/analysis/technical" \
    '{"issue_description":"Smoke issue","logs":"error line","errors":["timeout"],"code_snippets":["kubectl get pods"]}' \
    '"problem_statement"'

  log "checking knowledge/template list response shape"
  assert_api_get_is_array "${API_BASE}/knowledge"
  assert_api_get_is_array "${API_BASE}/templates"

  log "all smoke checks passed"
}

main "$@"
