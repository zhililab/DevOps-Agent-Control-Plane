#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG_FILE="$RUN_DIR/backend.log"
FRONTEND_LOG_FILE="$RUN_DIR/frontend.log"

BACKEND_PORT=8000
FRONTEND_PORT=3000

usage() {
  cat <<'EOF'
Usage:
  ./scripts/dev_stack.sh start|stop|restart|status|logs
EOF
}

ensure_run_dir() {
  mkdir -p "$RUN_DIR"
}

pid_from_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    cat "$pid_file"
  fi
}

is_pid_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  kill -0 "$pid" >/dev/null 2>&1
}

is_service_running() {
  local pid_file="$1"
  local pid
  pid="$(pid_from_file "$pid_file")"
  is_pid_running "$pid"
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local max_retries=40
  local retry=1

  while (( retry <= max_retries )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "[$name] ready: $url"
      return 0
    fi
    sleep 1
    retry=$((retry + 1))
  done

  echo "[$name] did not become ready in time. Check logs:"
  echo "  - $BACKEND_LOG_FILE"
  echo "  - $FRONTEND_LOG_FILE"
  return 1
}

start_backend() {
  if is_service_running "$BACKEND_PID_FILE"; then
    local existing_pid
    existing_pid="$(pid_from_file "$BACKEND_PID_FILE")"
    echo "[backend] already running (pid=$existing_pid)"
    return 0
  fi

  if [[ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
    echo "[backend] missing virtualenv or uvicorn: backend/.venv/bin/uvicorn"
    echo "Run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[test]'"
    return 1
  fi

  echo "[backend] applying migrations..."
  (cd "$ROOT_DIR/backend" && ./.venv/bin/alembic upgrade head >/dev/null)

  echo "[backend] starting on :$BACKEND_PORT ..."
  (
    cd "$ROOT_DIR/backend"
    nohup ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" >"$BACKEND_LOG_FILE" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )
}

start_frontend() {
  if is_service_running "$FRONTEND_PID_FILE"; then
    local existing_pid
    existing_pid="$(pid_from_file "$FRONTEND_PID_FILE")"
    echo "[frontend] already running (pid=$existing_pid)"
    return 0
  fi

  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    echo "[frontend] missing node_modules"
    echo "Run: cd frontend && npm install"
    return 1
  fi

  echo "[frontend] starting on :$FRONTEND_PORT ..."
  (
    cd "$ROOT_DIR/frontend"
    nohup npm run dev -- --hostname 127.0.0.1 --port "$FRONTEND_PORT" >"$FRONTEND_LOG_FILE" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )
}

stop_service() {
  local pid_file="$1"
  local name="$2"
  local pid
  pid="$(pid_from_file "$pid_file")"

  if ! is_pid_running "$pid"; then
    echo "[$name] not running"
    rm -f "$pid_file"
    return 0
  fi

  echo "[$name] stopping (pid=$pid)..."
  kill "$pid" >/dev/null 2>&1 || true

  local wait_count=0
  while is_pid_running "$pid" && (( wait_count < 20 )); do
    sleep 0.5
    wait_count=$((wait_count + 1))
  done

  if is_pid_running "$pid"; then
    echo "[$name] forcing stop (pid=$pid)"
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  rm -f "$pid_file"
  echo "[$name] stopped"
}

start_all() {
  ensure_run_dir
  start_backend
  start_frontend
  wait_for_http "http://127.0.0.1:${BACKEND_PORT}/health" "backend"
  wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" "frontend"
  echo
  echo "Dev stack started."
  echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}"
  echo "Backend : http://127.0.0.1:${BACKEND_PORT}"
}

stop_all() {
  stop_service "$FRONTEND_PID_FILE" "frontend"
  stop_service "$BACKEND_PID_FILE" "backend"
}

status_all() {
  if is_service_running "$BACKEND_PID_FILE"; then
    echo "[backend] running (pid=$(pid_from_file "$BACKEND_PID_FILE")) http://127.0.0.1:${BACKEND_PORT}"
  else
    echo "[backend] stopped"
  fi

  if is_service_running "$FRONTEND_PID_FILE"; then
    echo "[frontend] running (pid=$(pid_from_file "$FRONTEND_PID_FILE")) http://127.0.0.1:${FRONTEND_PORT}"
  else
    echo "[frontend] stopped"
  fi

  echo "Logs:"
  echo "  - $BACKEND_LOG_FILE"
  echo "  - $FRONTEND_LOG_FILE"
}

logs_all() {
  ensure_run_dir
  touch "$BACKEND_LOG_FILE" "$FRONTEND_LOG_FILE"
  tail -n 100 -f "$BACKEND_LOG_FILE" "$FRONTEND_LOG_FILE"
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    start)
      start_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      stop_all
      start_all
      ;;
    status)
      status_all
      ;;
    logs)
      logs_all
      ;;
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
