#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/k8s_deploy.sh render|dry-run|apply|verify

Commands:
  render   Render kustomize manifests for inspection.
  dry-run  Validate manifests via client-side dry-run.
  apply    Apply manifests to current kubectl context.
  verify   Check rollout status and recent logs.
EOF
}

ensure_cluster() {
  if ! kubectl cluster-info >/dev/null 2>&1; then
    echo "No reachable Kubernetes cluster for current kubectl context."
    echo "Please configure context first, then re-run."
    exit 2
  fi
}

verify_rollout() {
  kubectl -n personal-agent rollout status deployment/backend --timeout=120s
  kubectl -n personal-agent rollout status deployment/frontend --timeout=120s
  kubectl -n personal-agent get pods,svc,ingress
  kubectl -n personal-agent logs deployment/backend --tail=120
  kubectl -n personal-agent logs deployment/frontend --tail=120
}

case "${1:-}" in
  render)
    kubectl kustomize "$ROOT_DIR/k8s"
    ;;
  dry-run)
    ensure_cluster
    kubectl apply --dry-run=client --validate=false -k "$ROOT_DIR/k8s"
    ;;
  apply)
    ensure_cluster
    kubectl apply -k "$ROOT_DIR/k8s"
    ;;
  verify)
    ensure_cluster
    verify_rollout
    ;;
  *)
    usage
    exit 2
    ;;
esac
