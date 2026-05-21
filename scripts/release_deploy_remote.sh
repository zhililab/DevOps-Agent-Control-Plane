#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${DEPLOY_CONFIG:-$ROOT_DIR/.deploy.env}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[release-deploy] missing config: $CONFIG_FILE"
  echo "[release-deploy] create it from .deploy.env.example or set DEPLOY_CONFIG=/path/to/config"
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$CONFIG_FILE"
set +a

REMOTE_SSH="${REMOTE_SSH:-root@1.117.63.81}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/root/code/personal-agent-ws/personal-agent}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-master}"
CHECK_CMD="${CHECK_CMD:-make qa-fast}"
REMOTE_RESET_DB="${REMOTE_RESET_DB:-0}"
PUBLIC_HOST="${PUBLIC_HOST:-1.117.63.81}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-${1:-}}"

if [[ -z "${DB_PASSWORD:-}" ]]; then
  echo "[release-deploy] DB_PASSWORD is required in $CONFIG_FILE"
  exit 2
fi

if [[ -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="chore: release deploy $(date +%Y-%m-%d-%H%M)"
fi

shell_quote() {
  printf "%q" "$1"
}

log() {
  echo "[release-deploy] $*"
}

cd "$ROOT_DIR"

if git check-ignore -q .deploy.env; then
  :
else
  echo "[release-deploy] refusing to continue: .deploy.env is not ignored"
  exit 2
fi

log "running local gate: $CHECK_CMD"
eval "$CHECK_CMD"

log "staging local changes"
git add -A

if git diff --cached --quiet; then
  log "no staged changes; skipping commit"
else
  log "committing: $COMMIT_MESSAGE"
  git commit -m "$COMMIT_MESSAGE"
fi

log "pushing $GIT_REMOTE $GIT_BRANCH"
git push "$GIT_REMOTE" "$GIT_BRANCH"

remote_cmd="cd $(shell_quote "$REMOTE_APP_DIR")"
remote_cmd+=" && git fetch --prune"
remote_cmd+=" && git checkout $(shell_quote "$GIT_BRANCH") -f"
remote_cmd+=" && git reset --hard $(shell_quote "$GIT_REMOTE/$GIT_BRANCH")"
remote_cmd+=" && DB_PASSWORD=$(shell_quote "$DB_PASSWORD")"
remote_cmd+=" RESET_DB=$(shell_quote "$REMOTE_RESET_DB")"
remote_cmd+=" PUBLIC_HOST=$(shell_quote "$PUBLIC_HOST")"
if [[ -n "${APP_ENTITLEMENT_SECRET:-}" ]]; then
  remote_cmd+=" APP_ENTITLEMENT_SECRET=$(shell_quote "$APP_ENTITLEMENT_SECRET")"
fi
if [[ -n "${APP_BUSINESS_TIMEZONE:-}" ]]; then
  remote_cmd+=" APP_BUSINESS_TIMEZONE=$(shell_quote "$APP_BUSINESS_TIMEZONE")"
fi
remote_cmd+=" make server-deploy"

log "deploying on $REMOTE_SSH:$REMOTE_APP_DIR"
ssh -x "$REMOTE_SSH" "$remote_cmd"

log "remote deployment completed"
log "open: http://$PUBLIC_HOST"
log "health: http://$PUBLIC_HOST/health"
