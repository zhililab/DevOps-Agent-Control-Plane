#!/usr/bin/env bash

set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WATCH_MODE=0
UNTIL_PASS_MODE=0
INTERVAL_SECONDS=5
ROUND=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/test_cycle.sh [--watch] [--until-pass] [--interval SECONDS]

Options:
  --watch         Keep running tests in a loop.
  --until-pass    Retry until all tests pass, then exit.
  --interval N    Seconds between retries (default: 5).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --watch)
      WATCH_MODE=1
      shift
      ;;
    --until-pass)
      UNTIL_PASS_MODE=1
      shift
      ;;
    --interval)
      INTERVAL_SECONDS="${2:-}"
      if [[ -z "$INTERVAL_SECONDS" || ! "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
        echo "Invalid --interval value: ${2:-<empty>}"
        exit 2
      fi
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "$WATCH_MODE" -eq 1 && "$UNTIL_PASS_MODE" -eq 1 ]]; then
  echo "Use either --watch or --until-pass, not both."
  exit 2
fi

run_backend_tests() {
  echo "[backend] running pytest..."
  if [[ -x "$ROOT_DIR/backend/.venv/bin/pytest" ]]; then
    (cd "$ROOT_DIR/backend" && ./.venv/bin/pytest -q)
  else
    (cd "$ROOT_DIR/backend" && python3 -m pytest -q)
  fi
}

run_frontend_tests() {
  echo "[frontend] running npm test..."
  (cd "$ROOT_DIR/frontend" && npm test)
}

run_all_tests() {
  ROUND=$((ROUND + 1))
  echo
  echo "=== Test round ${ROUND} @ $(date '+%Y-%m-%d %H:%M:%S') ==="
  run_backend_tests
  local backend_status=$?
  run_frontend_tests
  local frontend_status=$?

  if [[ "$backend_status" -eq 0 && "$frontend_status" -eq 0 ]]; then
    echo "Round ${ROUND}: PASS"
    return 0
  fi

  echo "Round ${ROUND}: FAIL (backend=${backend_status}, frontend=${frontend_status})"
  return 1
}

if [[ "$WATCH_MODE" -eq 0 && "$UNTIL_PASS_MODE" -eq 0 ]]; then
  run_all_tests
  exit $?
fi

if [[ "$WATCH_MODE" -eq 1 ]]; then
  while true; do
    run_all_tests || true
    echo "Sleeping ${INTERVAL_SECONDS}s before next round..."
    sleep "$INTERVAL_SECONDS"
  done
fi

while true; do
  if run_all_tests; then
    echo "All tests passed. Stopping retries."
    exit 0
  fi
  echo "Sleeping ${INTERVAL_SECONDS}s before retry..."
  sleep "$INTERVAL_SECONDS"
done
