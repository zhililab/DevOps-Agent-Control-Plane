#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-personal-agent}"
DOMAIN="${DOMAIN:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
BACKEND_IMAGE="${BACKEND_IMAGE:-personal-agent-backend:k3d}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-personal-agent-frontend:k3d}"
INGRESS_CLASS="${INGRESS_CLASS:-traefik}"

if [[ -z "$DOMAIN" ]]; then
  echo "[deploy-k3d] missing DOMAIN env. Example: DOMAIN=agent.example.com"
  exit 2
fi

if [[ -z "$DB_PASSWORD" ]]; then
  echo "[deploy-k3d] missing DB_PASSWORD env."
  exit 2
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[deploy-k3d] required command not found: $cmd"
    exit 2
  fi
}

log() {
  echo "[deploy-k3d] $*"
}

create_cluster_if_needed() {
  if k3d cluster list --no-headers 2>/dev/null | awk '{print $1}' | grep -qx "$CLUSTER_NAME"; then
    log "k3d cluster already exists: $CLUSTER_NAME"
    return
  fi

  log "creating k3d cluster: $CLUSTER_NAME"
  k3d cluster create "$CLUSTER_NAME" \
    --servers 1 \
    --agents 0 \
    -p "80:80@loadbalancer" \
    -p "443:443@loadbalancer"
}

ensure_k3d_context() {
  local expected_ctx="k3d-${CLUSTER_NAME}"

  if ! kubectl config get-contexts -o name | grep -qx "$expected_ctx"; then
    echo "[deploy-k3d] expected kubectl context not found: $expected_ctx"
    echo "[deploy-k3d] available contexts:"
    kubectl config get-contexts -o name || true
    exit 2
  fi

  kubectl config use-context "$expected_ctx" >/dev/null
  log "using kubectl context: $expected_ctx"
}

assert_cluster_reachable() {
  if ! kubectl cluster-info >/tmp/personal-agent-k3d-cluster-info.log 2>&1; then
    echo "[deploy-k3d] kubectl cannot reach cluster with current context."
    cat /tmp/personal-agent-k3d-cluster-info.log
    exit 2
  fi
}

build_and_load_images() {
  log "building backend image: $BACKEND_IMAGE"
  docker build -f "$ROOT_DIR/backend/Dockerfile" -t "$BACKEND_IMAGE" "$ROOT_DIR"

  log "building frontend image: $FRONTEND_IMAGE"
  docker build -f "$ROOT_DIR/frontend/Dockerfile" -t "$FRONTEND_IMAGE" "$ROOT_DIR"

  log "importing images into k3d"
  k3d image import "$BACKEND_IMAGE" -c "$CLUSTER_NAME"
  k3d image import "$FRONTEND_IMAGE" -c "$CLUSTER_NAME"
}

apply_manifests() {
  log "applying namespace and secrets"
  kubectl create namespace personal-agent --dry-run=client -o yaml | kubectl apply -f -

  kubectl create secret generic postgres-secret \
    -n personal-agent \
    --from-literal=POSTGRES_DB=personal_agent \
    --from-literal=POSTGRES_USER=postgres \
    --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl create secret generic backend-secret \
    -n personal-agent \
    --from-literal=DATABASE_URL="postgresql+psycopg://postgres:${DB_PASSWORD}@postgres:5432/personal_agent" \
    --dry-run=client -o yaml | kubectl apply -f -

  log "applying k8s manifests (k3d image + ingress host/class replacements)"
  kubectl kustomize "$ROOT_DIR/k8s" \
    | sed "s|ghcr.io/your-org/personal-agent-backend:latest|$BACKEND_IMAGE|g" \
    | sed "s|ghcr.io/your-org/personal-agent-frontend:latest|$FRONTEND_IMAGE|g" \
    | sed "s|personal-agent.example.com|$DOMAIN|g" \
    | sed "s|kubernetes.io/ingress.class: nginx|kubernetes.io/ingress.class: ${INGRESS_CLASS}|g" \
    | kubectl apply -f -

  kubectl -n personal-agent rollout restart deployment/backend
  kubectl -n personal-agent rollout restart deployment/frontend
}

verify() {
  log "waiting for rollout"
  kubectl -n personal-agent rollout status statefulset/postgres --timeout=240s
  kubectl -n personal-agent rollout status deployment/backend --timeout=240s
  kubectl -n personal-agent rollout status deployment/frontend --timeout=240s

  log "resources"
  kubectl -n personal-agent get pods,svc,ingress

  log "done. access URL: http://$DOMAIN"
}

main() {
  require_cmd docker
  require_cmd kubectl
  require_cmd k3d

  create_cluster_if_needed
  ensure_k3d_context
  assert_cluster_reachable
  build_and_load_images
  apply_manifests
  verify
}

main "$@"
