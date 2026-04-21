# Deploy Online with Kind (Kubernetes on Docker)

This guide deploys Personal Agent to a single Linux server using **Kind** (K8s in Docker) and exposes it on ports 80/443.

## 1) Server prerequisites

- OS: CentOS/RHEL-compatible
- Docker installed and running
- `kubectl` installed
- `kind` installed
- Security Group/Firewall open: `80`, `443`, `22`
- A public IP bound to this server

Check public IP (run on server):

```bash
curl -4 ifconfig.me
```

## 2) DNS

Create an `A` record:

- Host: your domain (for example `agent.example.com`)
- Value: server public IP

## 3) Deploy

On the server, in this repo root:

```bash
export DOMAIN=agent.example.com
export DB_PASSWORD='replace-with-strong-password'

./scripts/deploy_kind_online.sh
```

What this script does:

- creates kind cluster with host port mapping `80/443`
- installs ingress-nginx controller
- builds backend/frontend images locally
- loads images into kind
- applies `k8s/` manifests and sets ingress host to `$DOMAIN`
- creates postgres/backend secrets
- waits for rollout readiness

## 4) Verify

```bash
kubectl -n personal-agent get pods,svc,ingress
curl -I http://$DOMAIN
curl -s http://$DOMAIN/api/health
```

## 5) Update deployment after code changes

```bash
export DOMAIN=agent.example.com
export DB_PASSWORD='same-password'
./scripts/deploy_kind_online.sh
```

## Notes / limitations

- Single-node, non-HA deployment.
- Suitable for MVP / small traffic.
- For production hardening, move to managed K8s + external PostgreSQL + TLS cert manager + multi-replica setup.
