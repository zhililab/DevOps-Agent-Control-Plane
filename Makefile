.PHONY: test test-watch test-until-pass qa-fast qa-visual qa-all e2e-orchestration product-language-check security-check smoke-check release-check release-deploy server-bootstrap server-deploy server-down server-restart server-status server-logs kind-deploy k3d-deploy dev-up dev-down dev-restart dev-status dev-logs templates-import-json templates-import-sql entitlement-token k8s-render k8s-dry-run k8s-apply k8s-verify

test:
	./scripts/test_cycle.sh

test-watch:
	./scripts/test_cycle.sh --watch --interval 10

test-until-pass:
	./scripts/test_cycle.sh --until-pass --interval 5

qa-fast:
	@set -e; \
	echo "[qa-fast] running backend tests + frontend tests + frontend build in parallel"; \
	( cd backend && if [ -x ./.venv/bin/pytest ]; then ./.venv/bin/pytest -q; else python3 -m pytest -q; fi ) & \
	pid_backend=$$!; \
	( cd frontend && npm test ) & \
	pid_frontend_test=$$!; \
	( cd frontend && npm run build ) & \
	pid_frontend_build=$$!; \
	wait $$pid_backend; \
	wait $$pid_frontend_test; \
	wait $$pid_frontend_build; \
	echo "[qa-fast] all checks passed"

qa-visual:
	cd frontend && npm run test:visual

qa-all: qa-fast qa-visual

e2e-orchestration:
	cd frontend && npm run test:e2e

product-language-check:
	./scripts/product_language_check.sh

security-check:
	./scripts/security_check.sh

smoke-check:
	./scripts/smoke_check.sh

release-check: qa-all e2e-orchestration product-language-check security-check k8s-render
	@echo "[release-check] qa-all, orchestration e2e, product language, security, and k8s render passed"

release-deploy:
	./scripts/release_deploy_remote.sh

server-bootstrap:
	./scripts/bootstrap_centos_kind.sh

server-deploy:
	./scripts/deploy_server_simple.sh

server-down:
	docker compose -f docker-compose.server.yml down

server-restart:
	docker compose -f docker-compose.server.yml down
	DB_PASSWORD=$${DB_PASSWORD:-change-me} docker compose -f docker-compose.server.yml up -d --build

server-status:
	docker compose -f docker-compose.server.yml ps

server-logs:
	docker compose -f docker-compose.server.yml logs -f --tail=120

kind-deploy:
	./scripts/deploy_kind_online.sh

k3d-deploy:
	./scripts/deploy_k3d_online.sh

dev-up:
	./scripts/dev_stack.sh start

dev-down:
	./scripts/dev_stack.sh stop

dev-restart:
	./scripts/dev_stack.sh restart

dev-status:
	./scripts/dev_stack.sh status

dev-logs:
	./scripts/dev_stack.sh logs

templates-import-json:
	cd backend && ./.venv/bin/python scripts/init_templates.py --mode json --source builtin

templates-import-sql:
	cd backend && ./.venv/bin/python scripts/init_templates.py --mode sql --source builtin

entitlement-token:
	cd backend && ./.venv/bin/python scripts/generate_entitlement.py --tier $${TIER:-pro} --ttl-seconds $${TTL_SECONDS:-3600}

k8s-render:
	kubectl kustomize k8s >/tmp/personal-agent-k8s-rendered.yaml && wc -l /tmp/personal-agent-k8s-rendered.yaml

k8s-dry-run:
	kubectl apply --dry-run=client --validate=false -k k8s

k8s-apply:
	kubectl apply -k k8s

k8s-verify:
	kubectl -n personal-agent rollout status deployment/backend --timeout=120s
	kubectl -n personal-agent rollout status deployment/frontend --timeout=120s
	kubectl -n personal-agent get pods,svc,ingress
	kubectl -n personal-agent logs deployment/backend --tail=120
	kubectl -n personal-agent logs deployment/frontend --tail=120
