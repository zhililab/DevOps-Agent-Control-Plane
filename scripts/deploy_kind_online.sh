#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-personal-agent}"
DOMAIN="${DOMAIN:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
BACKEND_IMAGE="${BACKEND_IMAGE:-personal-agent-backend:kind}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-personal-agent-frontend:kind}"

if [[ -z "$DOMAIN" ]]; then
  echo "[deploy] missing DOMAIN env. Example: DOMAIN=agent.yourdomain.com"
  exit 2
fi

if [[ -z "$DB_PASSWORD" ]]; then
  echo "[deploy] missing DB_PASSWORD env."
  exit 2
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[deploy] required command not found: $cmd"
    exit 2
  fi
}

log() {
  echo "[deploy] $*"
}

ensure_kind_context() {
  local expected_ctx="kind-${CLUSTER_NAME}"

  if ! kubectl config get-contexts -o name | grep -qx "$expected_ctx"; then
    echo "[deploy] expected kubectl context not found: $expected_ctx"
    echo "[deploy] available contexts:"
    kubectl config get-contexts -o name || true
    exit 2
  fi

  kubectl config use-context "$expected_ctx" >/dev/null
  log "using kubectl context: $expected_ctx"
}

assert_cluster_reachable() {
  if ! kubectl cluster-info >/tmp/personal-agent-cluster-info.log 2>&1; then
    echo "[deploy] kubectl cannot reach cluster with current context."
    echo "[deploy] details:"
    cat /tmp/personal-agent-cluster-info.log
    echo "[deploy] if you see login HTML/auth redirect, your kubectl context is not kind."
    echo "[deploy] run: kubectl config use-context kind-${CLUSTER_NAME}"
    exit 2
  fi
}

create_cluster_if_needed() {
  if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
    log "kind cluster already exists: $CLUSTER_NAME"
    return
  fi

  log "creating kind cluster: $CLUSTER_NAME"
  cat <<CFG >/tmp/personal-agent-kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
CFG

  kind create cluster --name "$CLUSTER_NAME" --config /tmp/personal-agent-kind-config.yaml
}

install_ingress_nginx() {
  if kubectl -n ingress-nginx get deploy ingress-nginx-controller >/dev/null 2>&1; then
    log "ingress-nginx already installed"
    return
  fi

  log "installing ingress-nginx controller"
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
  kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=180s
}

build_and_load_images() {
  log "building backend image: $BACKEND_IMAGE"
  docker build -f "$ROOT_DIR/backend/Dockerfile" -t "$BACKEND_IMAGE" "$ROOT_DIR"

  log "building frontend image: $FRONTEND_IMAGE"
  docker build -f "$ROOT_DIR/frontend/Dockerfile" -t "$FRONTEND_IMAGE" "$ROOT_DIR"

  log "loading images into kind"
  kind load docker-image "$BACKEND_IMAGE" --name "$CLUSTER_NAME"
  kind load docker-image "$FRONTEND_IMAGE" --name "$CLUSTER_NAME"
}

apply_manifests() {
  log "applying postgres secret"
  kubectl create namespace personal-agent --dry-run=client -o yaml | kubectl apply -f -

  kubectl create secret generic postgres-secret \
    -n personal-agent \
    --from-literal=POSTGRES_DB=personal_agent \
    --from-literal=POSTGRES_USER=postgres \
    --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

  log "applying k8s manifests (with kind image + ingress host replacements)"
  kubectl kustomize "$ROOT_DIR/k8s" \
    | sed "s|ghcr.io/your-org/personal-agent-backend:latest|$BACKEND_IMAGE|g" \
    | sed "s|ghcr.io/your-org/personal-agent-frontend:latest|$FRONTEND_IMAGE|g" \
    | sed "s|personal-agent.example.com|$DOMAIN|g" \
    | kubectl apply -f -

  log "overwriting backend DATABASE_URL secret"
  kubectl create secret generic backend-secret \
    -n personal-agent \
    --from-literal=DATABASE_URL="postgresql+psycopg://postgres:${DB_PASSWORD}@postgres:5432/personal_agent" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl -n personal-agent rollout restart deployment/backend
}

verify() {
  log "waiting for rollout"
  kubectl -n personal-agent rollout status statefulset/postgres --timeout=240s
  kubectl -n personal-agent rollout status deployment/backend --timeout=240s
  kubectl -n personal-agent rollout status deployment/frontend --timeout=240s

  log "resources"
  kubectl -n personal-agent get pods,svc,ingress

  log "done. Ensure DNS A record points DOMAIN=$DOMAIN to your server public IP."
  log "then open: http://$DOMAIN"
}

main() {
  require_cmd docker
  require_cmd kubectl
  require_cmd kind

  create_cluster_if_needed
  ensure_kind_context
  assert_cluster_reachable
  install_ingress_nginx
  build_and_load_images
  apply_manifests
  verify
}

main "$@"
