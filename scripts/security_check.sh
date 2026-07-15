#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECURITY_CHECK_BASE="${SECURITY_CHECK_BASE:-}"
SECURITY_AUDIT_LEVEL="${SECURITY_AUDIT_LEVEL:-high}"
SECURITY_ENTITLEMENT_SECRET="${SECURITY_ENTITLEMENT_SECRET:-${APP_ENTITLEMENT_SECRET:-}}"
SECURITY_RUNTIME_ONLY="${SECURITY_RUNTIME_ONLY:-0}"

log() {
  echo "[security-check] $*"
}

fail() {
  log "failed: $*"
  exit 1
}

assert_file_contains() {
  local file="$1"
  local pattern="$2"
  if ! grep -Fq "$pattern" "$file"; then
    fail "$file missing '$pattern'"
  fi
}

curl_status() {
  local url="$1"
  curl --connect-timeout 3 --max-time 10 -sS -o /tmp/personal-agent-security-body.txt -w "%{http_code}" "$url" || true
}

assert_status() {
  local url="$1"
  local expected="$2"
  local status
  status="$(curl_status "$url")"
  if [[ "$status" != "$expected" ]]; then
    log "unexpected status for $url: got=$status expected=$expected"
    cat /tmp/personal-agent-security-body.txt || true
    return 1
  fi
}

assert_runtime_header() {
  local header_file="$1"
  local header_name="$2"
  if ! grep -iq "^${header_name}:" "$header_file"; then
    fail "runtime response missing header: $header_name"
  fi
}

build_entitlement_token() {
  local tier="$1"
  local secret="$2"
  python3 - "$tier" "$secret" <<'PY'
import base64
import hashlib
import hmac
import json
import sys
import time

tier = sys.argv[1]
secret = sys.argv[2]
payload = {
    "tier": tier,
    "user_id": f"security-check-{tier}",
    "exp": int(time.time()) + 3600,
}
payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
encoded_payload = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
print(f"{encoded_payload}.{signature}")
PY
}

assert_runtime_security() {
  local base="$1"
  local header_file="/tmp/personal-agent-security-headers.txt"
  : > /tmp/personal-agent-security-body.txt

  log "checking runtime security at $base"
  curl --connect-timeout 3 --max-time 10 -sS -D "$header_file" -o /tmp/personal-agent-security-body.txt "$base/dashboard" >/dev/null
  assert_runtime_header "$header_file" "X-Content-Type-Options"
  assert_runtime_header "$header_file" "X-Frame-Options"
  assert_runtime_header "$header_file" "Referrer-Policy"
  assert_runtime_header "$header_file" "Permissions-Policy"
  assert_runtime_header "$header_file" "X-Permitted-Cross-Domain-Policies"
  assert_runtime_header "$header_file" "Content-Security-Policy-Report-Only"
  if grep -iq "^X-Powered-By:" "$header_file"; then
    fail "runtime response still exposes X-Powered-By"
  fi

  assert_status "$base/health" "200"
  assert_status "$base/dashboard" "200"
  assert_status "$base/orchestrate" "200"
  assert_status "$base/orchestrations" "200"

  local api_health_status
  api_health_status="$(curl_status "$base/api/health")"
  if [[ "$api_health_status" == "200" ]]; then
    fail "$base/api/health unexpectedly returned 200; canonical health route is /health"
  fi

  local run_payload='{"entry_source":"security_check","steps":[{"step_name":"Plan","agent_type":"planner","enabled":true},{"step_name":"Review","agent_type":"reviewer","enabled":true}],"daily_context":{"tasks":["security check"],"meetings":[],"blockers":[],"priorities":["security check"]},"persist_knowledge":false,"persist_template":false}'
  local missing_status
  missing_status="$(curl --connect-timeout 3 --max-time 10 -sS -X POST "$base/api/orchestrations/run" -H "Content-Type: application/json" -d "$run_payload" -o /tmp/personal-agent-security-body.txt -w "%{http_code}" || true)"
  if [[ "$missing_status" != "401" ]]; then
    log "unexpected missing-entitlement status: $missing_status"
    cat /tmp/personal-agent-security-body.txt || true
    return 1
  fi

  local evaluation_write_status
  evaluation_write_status="$(curl --connect-timeout 3 --max-time 10 -sS -X POST "$base/api/evaluations/runs" \
    -H "Content-Type: application/json" \
    -d '{"mode":"deterministic","case_ids":["docs-only-pass"]}' \
    -o /tmp/personal-agent-security-body.txt \
    -w "%{http_code}" || true)"
  if [[ "$evaluation_write_status" != "401" ]]; then
    log "unexpected anonymous evaluation-write status: $evaluation_write_status"
    cat /tmp/personal-agent-security-body.txt || true
    return 1
  fi

  if [[ -z "$SECURITY_ENTITLEMENT_SECRET" ]]; then
    fail "SECURITY_ENTITLEMENT_SECRET or APP_ENTITLEMENT_SECRET is required for runtime tier-boundary checks"
  fi
  local free_token
  free_token="$(build_entitlement_token free "$SECURITY_ENTITLEMENT_SECRET")"
  local free_status
  free_status="$(curl --connect-timeout 3 --max-time 10 -sS -X POST "$base/api/orchestrations/run" \
    -H "Content-Type: application/json" \
    -H "X-Entitlement: $free_token" \
    -d "$run_payload" \
    -o /tmp/personal-agent-security-body.txt \
    -w "%{http_code}" || true)"
  if [[ "$free_status" != "403" ]]; then
    log "unexpected free-tier status: $free_status"
    cat /tmp/personal-agent-security-body.txt || true
    return 1
  fi

  local oversized_payload
  oversized_payload="$(python3 - <<'PY'
import json
print(json.dumps({
    "issue_description": "security oversized payload",
    "logs": "x" * 10001,
    "errors": [],
    "code_snippets": [],
}))
PY
)"
  local oversized_status
  oversized_status="$(curl --connect-timeout 3 --max-time 10 -sS -X POST "$base/api/analysis/technical" \
    -H "Content-Type: application/json" \
    -d "$oversized_payload" \
    -o /tmp/personal-agent-security-body.txt \
    -w "%{http_code}" || true)"
  if [[ "$oversized_status" != "422" && "$oversized_status" != "413" ]]; then
    log "unexpected oversized-payload status: $oversized_status"
    cat /tmp/personal-agent-security-body.txt || true
    return 1
  fi
}

cd "$ROOT_DIR"

log "checking static security configuration"
assert_file_contains "deploy/nginx/default.conf" "server_tokens off"
assert_file_contains "deploy/nginx/default.conf" "proxy_hide_header X-Powered-By"
assert_file_contains "deploy/nginx/default.conf" "X-Content-Type-Options"
assert_file_contains "deploy/nginx/default.conf" "X-Frame-Options"
assert_file_contains "deploy/nginx/default.conf" "Referrer-Policy"
assert_file_contains "deploy/nginx/default.conf" "Permissions-Policy"
assert_file_contains "deploy/nginx/default.conf" "X-Permitted-Cross-Domain-Policies"
assert_file_contains "deploy/nginx/default.conf" "Content-Security-Policy-Report-Only"
assert_file_contains "deploy/nginx/default.conf" "client_body_timeout"
assert_file_contains "deploy/nginx/default.conf" "proxy_read_timeout"
assert_file_contains "deploy/nginx/default.conf" "gzip on"
assert_file_contains "frontend/next.config.ts" "poweredByHeader: false"
assert_file_contains "docker-compose.server.yml" "APP_EVALUATION_WRITE_SECRET"
assert_file_contains "backend/app/services/evaluation_access.py" "hmac.compare_digest"

if [[ "$SECURITY_RUNTIME_ONLY" != "1" ]]; then
  log "running backend security tests"
  (
    cd backend
    if [[ -x ./.venv/bin/pytest ]]; then
      ./.venv/bin/pytest -q tests/test_security_hardening.py
    else
      python3 -m pytest -q tests/test_security_hardening.py
    fi
  )

  log "running frontend dependency audit at level=$SECURITY_AUDIT_LEVEL"
  (
    cd frontend
    set +e
    audit_output="$(npm audit --audit-level="$SECURITY_AUDIT_LEVEL" 2>&1)"
    audit_status=$?
    set -e
    printf '%s\n' "$audit_output"
    if [[ "$audit_status" -ne 0 ]]; then
      if [[ "$SECURITY_AUDIT_LEVEL" =~ ^(high|critical)$ ]] && ! grep -Eiq "Severity: (high|critical)" <<< "$audit_output"; then
        log "npm audit returned non-zero, but no high/critical advisory details were reported"
      else
        exit "$audit_status"
      fi
    fi
  )
else
  log "SECURITY_RUNTIME_ONLY=1; skipped host pytest and npm audit"
fi

if [[ -n "$SECURITY_CHECK_BASE" ]]; then
  assert_runtime_security "$SECURITY_CHECK_BASE"
else
  log "SECURITY_CHECK_BASE not set; skipped runtime gateway assertions"
fi

log "all security checks passed"
