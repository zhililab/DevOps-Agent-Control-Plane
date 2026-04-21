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
  curl -fsSL -o /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64
  chmod +x /usr/local/bin/kind
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
