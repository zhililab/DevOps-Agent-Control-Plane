# Deploy Online with K3d (Kubernetes on Docker)

Use this path when `kind` is blocked by old kernel capabilities (for example missing cgroup namespace support on CentOS 7 hosts).

## 1) Server prerequisites

- Docker installed and running
- `kubectl` installed
- `k3d` installed
- Security Group open: `80`, `443`, `22`

Install k3d:

```bash
curl -fsSL https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

## 2) Deploy

In repo root on server:

```bash
export DOMAIN=1.117.63.81.nip.io
export DB_PASSWORD='replace-with-strong-password'

make k3d-deploy
```

What the script does:

- creates `k3d` cluster with host ports `80/443`
- builds backend/frontend images locally
- imports images into cluster
- applies k8s manifests with replaced image refs + ingress host
- switches ingress class to `traefik` by default
- waits for postgres/backend/frontend rollout

## 3) Verify

```bash
kubectl -n personal-agent get pods,svc,ingress
curl -I http://$DOMAIN
curl -s http://$DOMAIN/health
```

## Notes

- single-node, non-HA deployment for MVP.
- if you use your own ingress class, set `INGRESS_CLASS` when deploying:

```bash
INGRESS_CLASS=nginx make k3d-deploy
```
