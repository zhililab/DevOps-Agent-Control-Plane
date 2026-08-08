

<p align="center">
  <img src="docs/assets/devops-agent-control-plane-hero.png" alt="DevOps Agent Control Plane - trusted AI release governance for PR and CI" width="1200" />
</p>

# DevOps Agent Control Plane MVP

Producto actual: un DevOps Agent Control Plane desplegable. Se centra en la ejecución determinista de múltiples agentes, historial de flujos de trabajo reproducible, instantáneas de estado con puntos de control, controles del ciclo de vida de la cola, límites de nivel conscientes de derechos, Facturación Manual V1 y un proceso de incorporación tutorial orientado al comprador. Comercialmente, esto se enmarca como una ejecución de flujos de trabajo confiable antes de ampliar la amplitud general del asistente.

Aplicación estilo monorepo con:
- `frontend/`: UI Next.js + TypeScript
- `backend/`: API FastAPI + SQLAlchemy
- PostgreSQL scaffolding (opcional para local vía Docker), con SQLite por defecto para un arranque rápido

Mapa de documentación: `docs/README.md`. Estrategia comercial actual, ruta de demostración tutorial y notas del registro de patrones de orquestación: `docs/agent-orchestration-commercial-strategy.md`.

## Estructura del Proyecto

```text
.
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── profile/
│   │   ├── today/
│   │   ├── reflection/
│   │   └── history/
│   └── components/
└── docker-compose.yml
```

## Características MVP

### Superficie actual del MVP
- Orquestación de flujos de trabajo orientada a DevOps a través de pasos de Planner, Analyzer y Reviewer.
- Historial de orquestación reproducible respaldado por registros de pasos persistidos, no texto regenerado.
- Libro mayor de historial de orquestación con prioridad de precisión, con hashes de carga útil JSON canónica y verificación de integridad.
- Capa de Confianza de Equipo V1 con metadatos ligeros de equipo/solicitante/aprobador e instantáneas de puntos de control para demostraciones de equipos pequeños.
- Marcas de tiempo de auditoría UTC con derivación de fecha comercial `Asia/Shanghai` para precisión en el historial diario.
- Registros smoke/sistema etiquetados por `record_source` y ocultos en las vistas de historial personal por defecto.
- Ciclo de vida de cola asíncrono con línea de tiempo de estado, reintento y comportamiento de cancelación.
- Plantillas de flujo de trabajo para definiciones de pasos de orquestación reutilizables, con metadatos de patrón y metadatos de política para nivel requerido, nivel de riesgo, requisito de aprobación, alcance de herramientas y unidades de trabajo facturables.
- Adaptador PR/CI Real V1 que captura URL del PR, resumen de diff, resumen de log CI, entorno objetivo y riesgo de cambio como paquete de evidencia auditado para la puerta de lanzamiento.
- Soporte de token de derecho firmado para límites de nivel free/pro/power.
- Puerta de aprobación humana para plantillas de flujo de trabajo de alto riesgo antes de la ejecución sincrónica o en cola.
- Observabilidad de monetización para verificaciones de capacidad, verificaciones de cuota, eventos de uso, bloqueos de actualización, salud de la cola y agregación de KPIs.
- UI comercial orientada al comprador con una cáscara de control-plane pulida, navegación categorizada, vista previa animada de flujo de trabajo y una ruta tutorial interactiva desde la ejecución hasta la evidencia reproducible y la sugerencia de actualización.
- Resiliencia de la página comercial ante tiempos de espera parciales de API: el perfil de suscripción, los contadores de uso, el feed de auditoría y Commercial Signal se actualizan de forma independiente para que un feed lento no oculte un plan activo.
- Agregación de ROI V2 que incorpora el valor de la puerta de lanzamiento a nivel de ejecución en Commercial Signal y los KPIs del panel.
- Exportación de Evidencia V1 que expone paquetes de evidencia redactados en Markdown/JSON para pilotos del comprador.
- Pack de Escenarios de Piloto V2 que proporciona cinco escenarios fijos de lanzamiento del comprador que se pueden cargar desde `/tutorial` o `/orchestrate?scenario=...`.
- Informe de Preparación de Piloto V1 que agrega ejecuciones completadas, exportabilidad de evidencia, cobertura de libro mayor/puntos de control, completitud de metadatos de aprobación y valor de piloto estimado.
- Informe de Cierre de Piloto V1 que transforma la preparación, finalización de escenarios, evidencia de ROI, integridad del libro mayor/puntos de control y señales de actualización Power en un informe seguro para el comprador.
- Cierre Guiado de Piloto V2 que guía al comprador a través de los cinco escenarios fijos uno por uno, muestra el siguiente escenario a ejecutar y marca la revisión del comprador como lista solo cuando pasan todas las verificaciones de evidencia, libro mayor, punto de control y metadatos.
- Laboratorio de Calidad de Agentes V1 que añade una capa de observación opcional del modelo Volcengine Ark, registros versionados de prompt/modelo/token/latencia/costo, un conjunto de evaluación PR/CI fijo de 25 casos, retroalimentación humana append-only y evidencia medida de Baseline/Pilot.
- Utilidades de conocimiento y plantillas de prompt que admiten reutilización en torno a flujos de trabajo de orquestación.
- Las rutas existentes de plan diario, reflexión, análisis técnico, tarea y perfil permanecen disponibles para compatibilidad y soporte de flujo de trabajo personal.

### Modelos de datos
- `UserProfile`
- `Task`
- `ReflectionEntry`
- `AgentRunLog`
- `DailyPlan`
- `TechnicalAnalysis`
- `NoteEntry`
- `PromptTemplate`
- `WorkflowOrchestration`
- `WorkflowStepRun`
- `WorkflowTemplate`
- `WorkflowQueueJob`
- `WorkflowQueueEvent`
- `WorkflowCheckpoint`
- `HistoryEvent`
- `SubscriptionProfile`
- `UsageCounter`
- `MonetizationEvent`
- `LlmInvocation`
- `EvaluationRun`
- `EvaluationCaseResult`
- `DecisionFeedback`
- `PilotMeasurement`

### APIs
- `POST /api/profile`: create profile
- `PUT /api/profile/{id}`: update profile
- `GET /api/profile/{id}`: get profile
- `POST /api/plans/daily`: submit daily context, generate deterministic plan, persist result
- `GET /api/plans/history`: retrieve saved daily plans; defaults to user records, use `include_system=true` for smoke/system audit records
- `POST /api/reflections/daily`: submit reflection inputs, generate deterministic daily summary, persist result
- `GET /api/reflections/history`: retrieve saved structured reflections; defaults to user records, use `include_system=true` for smoke/system audit records
- `POST /api/analysis/technical`: submit technical issue context and generate structured analysis
- `GET /api/analysis/history`: retrieve saved technical analyses; defaults to user records, use `include_system=true` for smoke/system audit records
- `POST /api/knowledge`: create knowledge entry
- `GET /api/knowledge`: list knowledge entries with optional `q`/`tag` filters
- `GET /api/knowledge/{id}`: get knowledge entry
- `PUT /api/knowledge/{id}`: update knowledge entry
- `DELETE /api/knowledge/{id}`: delete knowledge entry
- `POST /api/templates`: create reusable prompt template
- `GET /api/templates`: list templates with optional `q`/`tag` filters
- `GET /api/templates/init/json`: get built-in template initialization data (JSON)
- `GET /api/templates/init/sql`: get built-in template initialization SQL
- `POST /api/templates/import/json`: import templates via JSON payload or built-in set
- `POST /api/templates/import/sql`: import templates via SQL payload or built-in SQL
- `GET /api/templates/{id}`: get template
- `PUT /api/templates/{id}`: update template
- `DELETE /api/templates/{id}`: delete template
- `POST /api/orchestrations/run`: run deterministic multi-agent orchestration (Planner/Analyzer/Reviewer)
- `GET /api/orchestrations/history`: list orchestration runs with status/tier/team filters and ledger integrity summaries
- `GET /api/orchestrations/{id}`: get orchestration run detail with step replay
- `GET /api/orchestrations/{id}/history-events`: inspect immutable ledger events and integrity status for a run
- `GET /api/orchestrations/{id}/checkpoints`: inspect checkpoint snapshots and payload hash status for a run
- `GET /api/orchestrations/{id}/evidence`: export a redacted Markdown/JSON evidence bundle for a run
- `GET /api/orchestrations/metrics`: orchestration KPI metrics (`days=7|30|...`)
- `GET /api/orchestrations/pilot-scenarios`: list the five fixed Pilot Scenario Pack V2 scenarios
- `POST /api/orchestrations/queue/run`: enqueue orchestration run (async)
- `GET /api/orchestrations/queue/history`: list queue jobs (status/team/attempts snapshot)
- `GET /api/orchestrations/queue/{job_id}`: get queue job status with real queue events and checkpoint timeline payload
- `POST /api/orchestrations/queue/{job_id}/retry`: retry failed/canceled queue job, optionally with `actor`
- `POST /api/orchestrations/queue/{job_id}/cancel`: request queue job cancellation, optionally with `actor`
- `POST /api/orchestrations/templates`: create orchestration workflow template
- `PUT /api/orchestrations/templates/{id}`: update orchestration workflow template
- `GET /api/orchestrations/templates`: list orchestration workflow templates
- `GET /api/orchestrations/templates/export`: export orchestration workflow templates
- `GET /api/orchestrations/templates/init/json`: get built-in orchestration workflow templates
- `POST /api/orchestrations/templates/import/builtin`: import or refresh built-in orchestration workflow templates
- `POST /api/orchestrations/templates/import`: import orchestration workflow templates
- `GET /api/evaluations/provider-status`: inspect provider readiness without exposing credentials
- `GET /api/evaluations/cases`: list the versioned 25-case PR/CI evaluation set
- `POST /api/evaluations/runs`: run deterministic or explicitly configured live-model evaluation (production write access required)
- `GET /api/evaluations/runs/latest`: inspect the latest quality metrics and case results
- `GET /api/evaluations/invocations`: inspect model, prompt version, tokens, latency, cost, and status
- `POST /api/evaluations/feedback`: append accept/reject/correct human feedback (production write access required)
- `GET /api/evaluations/feedback-summary`: calculate acceptance, correction, reviewed accuracy, and error rates
- `POST /api/evaluations/pilot-measurements`: record observed Baseline/Pilot measurements (production write access required)
- `GET /api/evaluations/pilot-comparison`: compare measured Baseline and Pilot values separately from estimated ROI

### Proveedor LLM Real Opcional

La política de lanzamiento determinista sigue siendo la autoridad de ejecución. El proveedor es una capa de observación consultiva utilizada para evaluación y evidencia operativa.

```bash
APP_LLM_ENABLED=true
APP_LLM_PROVIDER=volcengine_ark_coding_plan
APP_LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
APP_LLM_API_KEY=<rotated-secret>
APP_LLM_MODEL=doubao-seed-2.0-code
APP_LLM_PROMPT_VERSION=pr-ci-gate.v1
APP_EVALUATION_WRITE_SECRET=<independent-random-secret>
```

Utilice el endpoint OpenAI-compatible para Planes de Codificación para la ruta de evaluación respaldada por suscripción. No comprometa las claves y gire cualquier clave expuesta en capturas de pantalla, registros o chat. Las mutaciones de evaluación en producción requieren `X-Evaluation-Access`; este secreto de escritura independiente nunca debe ser la clave API del proveedor. Los precios de tokens de entrada/salida son configurables para que `estimated_cost_usd` pueda reflejar el modelo seleccionado; los planes de suscripción pueden dejar precios marginales de tokens en cero mientras retienen evidencia de token y latencia. Los resultados locales de pre-lanzamiento y de producción del 2026-07-16 del Proveedor se registran por separado en `docs/agent-quality-evidence.md`.
- `GET /api/observability/monetization`: monetization observability aggregation (`days=7|30`)
- `GET /api/monetization/profile`: read subscription profile by `subject`
- `GET /api/monetization/usage`: read usage counters by `subject`
- `GET /api/monetization/events`: read newest-first monetization event audit feed, optionally scoped by `subject`
- `GET /api/monetization/entitlement`: issue a signed orchestration entitlement from an active Manual Billing subject
- `GET /api/monetization/commercial-metrics`: read Commercial Signal (`days=7|30`, optional `subject`) with billing-period plan usage, window activity, policy blocks, billable work units, ROI summary, top templates, and anomaly hints
- `GET /api/monetization/pilot-report`: read Pilot Readiness (`days=7|30`, optional `subject` and `team_subject`) for buyer trial acceptance, including `scenario_completion` progress and next scenario guidance
- `GET /api/monetization/pilot-closeout`: read a Markdown-ready Pilot Closeout report (`days=7|30`, optional `subject` and `team_subject`) with Buyer Review Status, scenario completion, missing evidence, value generated, and Power upgrade recommendation
- `POST /api/monetization/checkout/manual`: activate or change a manual billing subscription
- `POST /api/monetization/cancel`: schedule subscription cancellation at period end
- `POST /api/monetization/reactivate`: clear a pending manual cancellation
- `POST /api/tasks`: create task
- `GET /api/tasks`: list tasks
- `PUT /api/tasks/{id}`: update task
- `POST /api/reflections`: create reflection
- `GET /api/reflections`: list reflections
- `PUT /api/reflections/{id}`: update reflection

### Páginas de la UI
- `/dashboard`
- `/profile`
- `/today`
- `/reflection`
- `/technical-analysis`
- `/orchestrate`
- `/orchestrations`
- `/monetization`
- `/tutorial`
- `/evaluation`
- `/knowledge`
- `/templates`
- `/history`

## Inicio Local

## Demostración de Conversión de Piloto

La demostración comercial actual es guiada por escenarios:

1. Abra `/monetization`, active o actualice un plan Power para `demo-user`.
2. Abra `/tutorial`, revise el progreso del piloto de estilo `0/5 completados`, luego elija `Run Scenario` para la siguiente tarjeta del conjunto de datos del Piloto.
3. `/orchestrate?scenario=<id>` carga el contexto del adaptador PR/CI, entradas de planner/analyzer/reviewer, metadatos de aprobación y la plantilla de puerta de lanzamiento recomendada.
4. Ejecute la puerta con derecho de Power firmado y aprobación explícita.
5. Abra `/orchestrations`, verifique libro mayor/puntos de control, luego use `Export Evidence`, `Copy Markdown` o `Download Markdown`.
6. Abra `/monetization` para revisar `Commercial Signal`, `Pilot Readiness`, `Buyer Review Status`, finalización de escenarios agrupada, `Why Power`, y el informe de Cierre de Piloto para copiar/descargar.
7. Abra `/dashboard` para confirmar KPIs del comprador: Estimated Value, Review Time Saved, Blocked Risk Value y Pilot Ready.
8. Para evidencia de calidad, abra `/evaluation` para ejecutar el punto de referencia PR/CI fijo, revise métricas de retroalimentación humana, inspeccione telemetría de llamadas al modelo y compare las mediciones observadas de Baseline/Pilot.

## 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env  # optional
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

### Opcional: usar PostgreSQL

```bash
docker compose up -d postgres
```

Luego establezca en `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/personal_agent
```

Reinicie el backend.

## 2) Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Abra `http://localhost:3000`.

## Ejecución Automática para Validación de UI

Desde la raíz del repositorio, un solo comando para iniciar backend + frontend:

```bash
make dev-up
```

El inicio de desarrollo local ejecuta migraciones del backend y la misma verificación de inicialización de tabla principal utilizada por el despliegue del servidor antes de iniciar `uvicorn`.

Comandos compañeros útiles:

```bash
make dev-status   # show running status and URLs
make dev-logs     # stream backend/frontend logs
make dev-down     # stop both services
make dev-restart  # restart both services
```

## Despliegue Simplificado del Servidor (Ruta MVP Recomendada)

La entrada de despliegue recomendada para el MVP actual es la ruta del servidor Docker Compose. Proporciona un host siempre activo con PostgreSQL, FastAPI, Next.js y una puerta de enlace Nginx en el puerto `80`:

```bash
DB_PASSWORD='replace-with-strong-password' make server-deploy
```

La compil de la imagen del backend ahora usa por defecto:

`PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`

Aún puede anularlo cuando sea necesario:

```bash
PIP_INDEX_URL='https://pypi.tuna.tsinghua.edu.cn/simple' \
DB_PASSWORD='replace-with-strong-password' \
make server-deploy
```

Si el backend sigue reiniciándose después de los cambios de contraseña/entorno, restablezca una vez el volumen de datos antiguo de Postgres:

```bash
DB_PASSWORD='replace-with-strong-password' RESET_DB=1 make server-deploy
```

Si su contraseña de base de datos contiene caracteres de URL especiales (por ejemplo `@`, `#`, `:`), simplemente use `make server-deploy` (ahora se codifica automáticamente para el DSN del backend), o establ establ establ establezca explícitamente:

```bash
DB_PASSWORD='raw-password' DB_PASSWORD_URLENC='url-encoded-password' make server-deploy
```

Esto inicia:
- `postgres`
- `backend`
- `frontend`
- `gateway` (Nginx en el puerto `80`, enruta `/api` al backend)

El inicio del servidor ahora ejecuta: `python -m app.db_migration -> uvicorn`. El wrapper de migración aplica Alembic normalmente y puede sellar un esquema creado previamente antes de actualizar, lo que mantiene los despliegues de servidor reiniciables sin restablecer los datos.
Esto protege contra estados de migración parcialparcial que pueden causar errores de tiempo de ejecución de tabla faltante.

## Puerta de Derecho (Verificación de nivel listo para facturación)

Las APIs de orquestación ahora admiten token de derecho firmado:

- header: `X-Entitlement: <signed_token>`
- env:
  - `APP_ENVIRONMENT=local|staging|production`
  - `APP_ENTITLEMENT_REQUIRED=true|false`
  - `APP_ENTITLEMENT_SECRET=<strong-secret>`
  - `APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK=true|false` (non-production only)

Comportamiento de autenticación efectivo:

- En `production`, `X-Entitlement` firmado siempre es requer y la sustitución de `X-Subscription-Tier` está deshabilitada.
- En entornos no de producción, la sustitución de `X-Subscription-Tier` solo se honra cuando `APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK=true`.
- `APP_ENTITLEMENT_REQUIRED=true` fuerza `X-Entitlement` firmado en cada entorno.
- El token firmado es autoritativo cuando se proporcionan ambos headers (`X-Entitlement` anula el header de nivel heredado discordante).
- Los tokens expirados o con firma inválida devuelven errores `401` deterministas.
- La guardia de capacidad del nivel gratuito deniega ejecuciones de orquestación multi-paso con `403`.
- La frontend `/orchestrate` usa tokens de derechos firmados y ya no emite `X-Subscription-Tier`; el header heredado permanece como una sustitución explícita de la API solo para entornos no de producción.
- Los sujetos de Facturación Manual V1 ahora pueden cargar tokens de derechos firmados desde `/api/monetization/entitlement?subject=...`, por lo que una cuenta Pro/Power activada puede ejecutar directamente plantillas de orquestación compatibles desde `/orchestrate`.
- Volver a comprar un perfil de Facturación Manual expirado renueva su período de suscripción de 30 días sin eliminar el historial de uso o los eventos de auditoría.

Notas del contrato de observabilidad y cuota:

- Los campos de respuesta de `GET /api/orchestrations/metrics` son estables y están ordenados como:
  `period_days`, `total_runs`, `weekly_active_orchestrations`, `partial_success_rate`, `average_duration_ms`.
- `GET /api/orchestrations/history` se devuelve más recienteprimero para una agregación determinista del dashboard. Use `include_steps=false&include_integrity=false` para lecturas de dashboard/tendencia ligeras que no necesitannecesiten detalles de replay o estado del libro mayor.
- El historial de orquestación, el historial de cola, el libro mayor y las consultas de auditoría de monetización están respaldados por índices compuestos para un filtrado estable y una paginación más-primero a medida que crecen los datos.
- El límite de cuota/tasa de solicitud global devuelve `429 Too many requests. Please retry later.` una vez que se excede el límite configurado por ventana.
- Nota del contrato del dashboard: la ruta de backend de observabilidad de monetización es `GET /api/observability/monetization`; el cliente de la frontend usa esta ruta canónica.
- Nota del contrato de Commercial Signal: `/monetization` y `/dashboard` usan `GET /api/monetization/commercial-metrics` para unidades de trabajo facturables, resumen de ROI, bloqueos de política, plantillas de valor principal y sugerencias de anomalías comerciales. `UsageCounter` es la fuente de verdad para el uso de planes y la cuota del período de facturación; `usage_summary` permanece como una ventana de actividad limitada de 7D/30D. Los informes por sujeto coinciden tanto con el sujeto de facturación crudoraw como con el ID de sujeto derivado del derecho.

Genere un token local para pruebas:

```bash
make entitlement-token TIER=pro TTL_SECONDS=3600
```

Use el token generado en la página `/orchestrate` (campo Entitlement Token), o, páselo a través del header en las llamadas de la API.

Operaciones útiles:

```bash
make server-status
make server-logs
make server-restart
make server-down
```

Guía detallada: `docs/deploy-simple-server.md`.

## Commit de Lanzamiento y Despliegue Remoto

La configuración de despliegue privado local reside en `.deploy.env` y está intencionalmente ignorada por git. Use `.deploy.env.example`
como la plantilla rastreada.

Una vez completado el desarrollo, ejecute:

```bash
make release-deploy
```

Para migraciones que tocan historial almacenado, cree una copia de seguridad de PostgreSQL en el servidor antes de desplegar y mantenga `REMOTE_RESET_DB=0`.

El script de despliegue de lanzamiento:
- ejecuta la puerta configurada localmente (`CHECK_CMD`, por defecto `make qa-fast`)
- prepara y confirma los cambios locales
- empuja `origin master`
- SSH a `root@1.117.63.81`
- ejecuta `git fetch --prune`, `git checkout master -f`, `git reset --hard origin/master`
- ejecuta `make server-deploy` en el servidor con los valores de `.deploy.env`

Establezca `REMOTE_RESET_DB=1` en `.deploy.env` solo cuando la base de datos remota pueda ser descartada.

### Verificación de Despliegue

Después de `make server-deploy`, verifique el despliegue a través de la puerta de enlace:

```bash
make server-status
curl http://<server-host>/health
```

Luego abra las superficies de orquestación orientadas al usuario:

- `http://<server-host>/orchestrate`
- `http://<server-host>/orchestrations`
- `http://<server-host>/dashboard`

Para validación a nivel de API, ejecute una solicitud de orquestación pro/power firmada o use el campo de token de derecho en `/orchestrate`. El nivel gratuito aún debe denazar la orquestación multi-paso con un `403` determinista.

### Rutas de Acceso Público

Después de `make server-deploy`, las rutas públicas son servidas por la puerta de enlace. Reemplace `<server-host>` con la IP o dominiodominio del servidor:

- Inicio: `http://<server-host>/`
- Dashboard: `http://<server-host>/dashboard`
- Plan de Hoy: `http://<server-host>/today`
- Reflexión: `http://<server-host>/reflection`
- Análisis Técnico: `http://<server-host>/technical-analysis`
- Orquestar: `http://<server-host>/orchestrate`
- Historial de Orquestación: `http://<server-host>/orchestrations`
- Conocimiento: `http://<server-host>/knowledge`
- Plantillas: `http://<server-host>/templates`
- Health de la API: `http://<server-host>/health`

Si despliega con `DOMAIN=<server-ip>.nip.io`, las rutas equivalentes son:

- `http://<server-ip>.nip.io/`
- `http://<server-ip>.nip.io/dashboard`
- `http://<server-ip>.nip.io/health`

## Comandos de Migración

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
```

## Pruebas

Ejecute pruebas del backend:

```bash
cd backend
source .venv/bin/activate
pytest
```

La cobertura de pruebas actual incluye:
- inicio de la app
- endpoint `/health`
- generación de plan diario + persistencia + recuperación de historial
- generación de resumen de reflexión diaria + persistencia + recuperación de historial
- generación de análisis técnico + validación de solicitud + persistencia + recuperación de historial
- precisión de zona horaria comercial para fechasfechas de plan/reflexión/análisis diario y marcas de tiempo públicas marcadas en UTC
- filtrado por defecto de registros smoke/sistema del historial del usuario con acceso de auditoría `include_system=true`
- cobertura del script de verificación smoke para rutas de UI y APIs principales, incluyendo ejecución/historial/métricas de orquestación, ejecución/historial de cola, observabilidad de monetización y APIs de lectura de monetización
- ejecución de flujo de trabajo de orquestación + replay de pasos + recuperación de historial con fallback de fallo parcial
- creación de eventos del libro mayor de historial, relleno idempotente, verificación de hash de carga útil canónica y detección de manipulación
- límite de nivel free/pro/power para orquestación (restricción de un solo paso para free)
- CRUD de plantilla de orquestación + prueba de idaround-trip de importación/exportación
- CRUD de entrada de conocimiento + filtrado + casos extrem de ordenación/validación
- CRUD de plantilla de prompt + filtrado
- importación por lotes de plantilla de prompt (JSON/SQL) y biblioteca de inicio incorpor
- fallback de fallo frontend del dashboard/historial y mensajes de error sanitizados

Ejecute pruebas del frontend:

```bash
cd frontend
npm test
```

Ejecute pruebas de pila completa en un solo comando (raíz del repositorio):

```bash
make test
```

Ejecute verificaciones de calidad paraleen paralelo (raíz del repositorio):

```bash
# backend tests + frontend tests + frontend build (parallel)
make qa-fast

# visual baseline snapshots (dashboard, knowledge)
make qa-visual

# full quality chain
make qa-all

# real-browser orchestration flow
make e2e-orchestration

# security headers, entitlement boundaries, payload/rate-limit guardrails, and high-severity dependency audit
make security-check

# app smoke checks (routes + core API loops)
make smoke-check
```

Puerta previade prelanzamiento de lanzamiento:

```bash
make release-check
```

Esto ejecuta `qa-all`, el flujo E2E del navegador real `/orchestrate -> /orchestrations`, `security-check` y `k8s-render`.
La ruta de lanzamiento del MVP actual es el despliegue del servidor Docker Compose; k3d/k8s permanece disponible para la validación de despliegue posterior y no bloquea el lanzamiento de la ruta actual del servidor.

Opciones de despliegue K8s contenerizadasizado:

```bash
# Kind-based online deployment
make kind-deploy

# K3d-based online deployment (recommended fallback for older kernels)
make k3d-deploy
```

Modos de iteración continua (raíz del repositorio):

```bash
# keep running forever, every 10s
make test-watch

# retry until all tests pass, then stop
make test-until-pass
```

CI está configurado en `.github/workflows/ci.yml` con trabajos en paralelo:

- `backend-test`
- `frontend-test`
- `frontend-build`
- `visual-baseline`
- `integration-gate` (depende de todos los trabajos anteriores)

La guía de reutilización de diseño/movimiento está documentada en `docs/visual-guidelines.md`.
La lista de verificación de la puerta de lanzamiento está documentada en `docs/release-checklist.md`.
Las verificaciones de funcionalidad principal están documentadas en `docs/core-functionality-check.md`.
El flujo de demostración MVP está documentado en `docs/mvp-demo-runbook.md`; el paquete de prueba empresarial está en `docs/pilot-package-v1.md`.
La evidencia de despliegue se registra en `docs/deployment-evidence.md`.
La guía de despliegue en línea K3d está documentada en `docs/deploy-k3d-online.md`.

## Importación de Inicialización de Plantilla

Puede inicializar plantillas de prompt reutilizables en cualquier formato:

```bash
# JSON import using built-in starter library
curl -X POST http://localhost:8000/api/templates/import/json \
  -H "Content-Type: application/json" \
  -d '{"use_builtin": true, "upsert_by_name": true}'

# SQL import using built-in starter SQL
curl -X POST http://localhost:8000/api/templates/import/sql \
  -H "Content-Type: application/json" \
  -d '{"use_builtin": true, "reset_existing": false}'
```

O ejecute comandcomandos de ayuda locales desde la raíz del repositorio:

```bash
make templates-import-json
make templates-import-sql
```

Las plantillas de or de trabajo de orquestación integradas también están disponibles para `/orchestrate`:

```bash
curl -X POST http://localhost:8000/api/orchestrations/templates/import/builtin
```

El conjunto curado de orquestación se basa en el buje de operación actual del MVP de DevOps: puertas de lanzamiento, verificación de despliegue remoto, precisión del historial, endurecimiento de seguridad, rendimiento de consultasconsulta, recuperación de derechos, auditoría del ciclo de vida de la cola, integridad del libro mayor, preparación de migración de base de datos, QA visual, preparación de seguimiento de Kubernetes y verificaciones smoke de nivel gratuito.

## Limitaciones Actuales

Este MVP mantiene intencionalmente un alcance pequeño. Las restricciones actuales son:

- No se admite de búsqueda semántica/vectorial o ranking para la recuperación de conocimiento aún.
- El conocimiento y las plantillas solo admiten consulta de texto básica (`q`) y filtro de etiqueta exacta (`tag`) en la recuperación del backend.
- No hay separación RBAC/multi-tenant en la capa de la aplicación aún.
- La orquestación tiene una cola de tareas de fondo ligera de FastAPI, pero no un proceso de trabajador durable separado aún.
- La salida del análisis técnico es reglas en reglas deterministas (inspeccionable), no ranking generado por modelos.
- El asistente de comunicación y la Revisión Semanal son capacidades del roadmap; no hay páginas de UI ni APIs de producción actuales para esos flujos de trabajo.
- Los manifiestos de Kubernetes son listos para producción en un nivel básico, pero permanecen no-HA.
- Este lanzamiento aún evita integraciones externas y acciones externas autónomas.

## Endurecimiento de Seguridad (Actual)

- La limitación de tasa básica de la API está habilitada por defecto para solicitudes `/api/*`.
  - Knobs de entornoenv: `APP_RATE_LIMIT_ENABLED`, `APP_RATE_LIMIT_MAX_REQUESTS`, `APP_RATE_LIMIT_WINDOW_SECONDS`.
- Los registros de ejecución del agente se sanitizan para valores sensibles (`password`, `token`, `secret`, tokens bearer) antes de la persistencia.
- Las entradas del flujo de trabajo principal imponen tamaño máximo de carga útil/límites de elemento para reducir el riesgo de abuso y la presión de almacenamiento.

## Despliegue en Kubernetes (Primera Versión)

### 1) Construir y empujar imágenes

```bash
# repo root
docker build -f backend/Dockerfile -t ghcr.io/your-org/personal-agent-backend:latest .
docker build -f frontend/Dockerfile -t ghcr.io/your-org/personal-agent-frontend:latest .

docker push ghcr.io/your-org/personal-agent-backend:latest
docker push ghcr.io/your-org/personal-agent-frontend:latest
```

Actualice las direcciones de imagen en:
- `k8s/backend.yaml`
- `k8s/frontend.yaml`

### 2) Configurar secreto de PostgreSQL

```bash
cp k8s/postgres-secret.example.yaml /tmp/postgres-secret.yaml
# edit POSTGRES_PASSWORD in /tmp/postgres-secret.yaml
kubectl apply -f /tmp/postgres-secret.yaml
```

Importante: actualice la contraseña de `DATABASE_URL` en `k8s/backend.yaml` (`backend-secret`) para que coincida.

### 3) Validación de prueba de concepto (dry-run)

```bash
make k8s-dry-run
```

### 4) Aplicar recursos

```bash
make k8s-apply
```

### 5) Verificar rollout

```bash
make k8s-verify
```

Los recursos de K8s se encuentran bajo `k8s/`:
- namespace, postgres statefulset/service, backend, frontend, ingress

Guía detallada:
- `docs/k8s-deploy.md`
