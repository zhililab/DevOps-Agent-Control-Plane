#!/usr/bin/env bash

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[bootstrap] please run as root"
  exit 2
fi

log() {
  echo "[bootstrap] $*"
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "docker already installed"
  else
    log "installing docker"
    yum install -y yum-utils device-mapper-persistent-data lvm2
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  fi

  systemctl enable --now docker
  docker version >/dev/null
}

install_kubectl() {
  if command -v kubectl >/dev/null 2>&1; then
    log "kubectl already installed"
    return
  fi

  log "installing kubectl"
  cat >/etc/yum.repos.d/kubernetes.repo <<REPO
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/repodata/repomd.xml.key
REPO
  yum install -y kubectl
}

install_kind() {
  if command -v kind >/dev/null 2>&1; then
    log "kind already installed"
    return
  fi

  log "installing kind"
  local tmp_bin
  tmp_bin="$(mktemp /tmp/kind.XXXXXX)"

  # Prefer official URL, then common mirror endpoint for unstable networks.
  if ! curl -fL --retry 5 --retry-delay 2 --connect-timeout 10 \
    -o "$tmp_bin" \
    "https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64"; then
    log "official kind URL failed, retrying with mirror"
    curl -fL --retry 5 --retry-delay 2 --connect-timeout 10 \
      -o "$tmp_bin" \
      "https://ghproxy.com/https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64"
  fi

  install -m 0755 "$tmp_bin" /usr/local/bin/kind
  rm -f "$tmp_bin"

  # Repair a pre-existing broken file case.
  chmod 0755 /usr/local/bin/kind || true
}

install_basic_tools() {
  log "installing basic tools"
  yum install -y git make curl jq tar
}

main() {
  install_basic_tools
  install_docker
  install_kubectl
  install_kind

  log "versions"
  docker --version
  kubectl version --client=true
  kind version

  log "done"
}

main "$@"
