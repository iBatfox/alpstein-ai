# Alpstein AI — Runtime map (canonical)

**Doc status:** canonical (ops)  
**As-of:** 2026-05-28 (OPS-H1)  
**Tag baseline:** `recovery-runtime-stable-2026-05-28`  
**Audits:** [`recovery-runtime-source-of-truth-2026-05-28.md`](../audits/recovery-runtime-source-of-truth-2026-05-28.md) · [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md) · [`e1-9-unified-ingress-cutover-2026-05-28.md`](../audits/e1-9-unified-ingress-cutover-2026-05-28.md)

Single operator reference for **what runs**, **which ports matter**, and **what must not be touched**.

---

## 1. Canonical runtime topology

```text
Internet (443)
    → nginx n8n.alpstein-ai.ch
    → 127.0.0.1:15679  alpstein_n8n_compose
           → http://backend:8000  (alpstein_internal)
                → alpstein_backend
                → alpstein_postgres (DNS: postgres)

Meta Instagram webhook (443)
    → nginx api.alpstein-ai.ch exact /webhooks/meta
    → 127.0.0.1:18081  alpstein_backend (container port 8000)
           → backend dispatches to n8n Instagram ingress URL

Production workflow: alpstein-customer-ingress (aYrRmAGKhP4TJbG9)
```

| Container | Compose service | Network | Role |
|-----------|-----------------|---------|------|
| `alpstein_postgres` | `postgres` | `alpstein_internal` | Portable DB (`alpstein_postgres_data`) |
| `alpstein_backend` | `backend` | `alpstein_internal` | FastAPI / webhooks / AI orchestration |
| `alpstein_n8n_compose` | `n8n` | `alpstein_internal` | Customer ingress + integrations |

**Compose project:** `alpstein-ai`  
**CLI:** `docker compose` v2 only (see §9).

---

## 2. Public ingress map

| Public URL | Edge | Upstream | Workflow / path |
|------------|------|----------|-----------------|
| `https://n8n.alpstein-ai.ch/` | nginx TLS | `127.0.0.1:15679` | n8n UI + webhooks |
| `https://api.alpstein-ai.ch/webhooks/meta` | Meta → nginx TLS | `127.0.0.1:18081` exact route | Backend Meta intake; Instagram then dispatches to n8n |
| Instagram n8n ingress | backend → n8n | `https://n8n.alpstein-ai.ch` | `…/webhook/alpstein/unified-customer-ingress/instagram/incoming` |
| Telegram customer bot | Telegram → n8n | same | `…/webhook/alpstein-telegram-customer-trigger-unified-inactive/webhook` |
| Website Chat (production) | Browser → n8n | same | `…/webhook/alpstein/unified-customer-ingress/website-chat/incoming` |

**Not public:** backend container port `8000`, backend host bind `18081`, postgres `15433` — loopback only.

---

## 3. Internal-only services (loopback)

| Bind | Service | Notes |
|------|---------|--------|
| `127.0.0.1:15679` | `alpstein_n8n_compose` | **Production** n8n; nginx upstream |
| `127.0.0.1:18081` | `alpstein_backend` | Host nginx upstream for `api.alpstein-ai.ch/webhooks/meta`; compose binding `127.0.0.1:18081:8000` |
| `127.0.0.1:8000` | `alpstein_backend` | Legacy/dev overlay only; stale upstream here causes `502` if no host listener exists |
| `127.0.0.1:15433` | `alpstein_postgres` | Dev overlay; **not** legacy `15432` |
| `127.0.0.1:15678` | `integrationhubspot_n8n` | **HubSpot — do not modify** |

---

## 4. Port classification table

| Port | Class | Listener (2026-05-28) | Status |
|------|--------|------------------------|--------|
| **443 / 80** | Production public | nginx | Active (TLS → n8n) |
| **15679** | Production internal | `alpstein_n8n_compose` | **Canonical** |
| **18081** | Production internal | `alpstein_backend` | Backend host loopback bind for nginx exact `/webhooks/meta` route |
| **8000** | Container/internal or legacy dev bind | `alpstein_backend` container port | Do not use as nginx upstream unless a host listener is confirmed |
| **15433** | Dev / ops only | `alpstein_postgres` | Active |
| **15678** | Foreign (HubSpot) | `integrationhubspot_n8n` | Active — out of scope |
| **15680** | Reserved (compose default) | — | Use **15679** via `N8N_HOST_PORT=15679` |
| **8010** | Legacy deprecated | — | **No listener** — do not start host uvicorn here |
| **15432** | Legacy deprecated | — | **`backend_postgres` stopped** — do not use for portable stack |
| **8088 / 8090** | Dev-only | `python3 -m http.server` | **Unsafe if `0.0.0.0`** — bind `127.0.0.1` only |
| **18080** | Dev-only (docs) | optional widget static | Documented in Website Chat runbook |
| **5432** (host) | Non-Alpstein | system postgres | Separate from `alpstein_postgres` |

---

## 5. Forbidden / legacy ports and patterns

| Pattern | Why forbidden |
|---------|----------------|
| `BACKEND_BASE_URL=http://172.20.0.1:8010` | Legacy host backend — breaks with compose SoT |
| `docker-compose … --force-recreate` (v1.29) | `KeyError: ContainerConfig` on Docker 29 |
| Second n8n on **15679** | Volume / webhook conflict |
| Public `0.0.0.0` on dev static servers | Accidental exposure of widget test pages |
| n8n → `backend_postgres` / host `15432` | Wrong database vs `alpstein_postgres_data` |
| Modify HubSpot **15678** | Out of project scope |

---

## 6. Allowed operational commands

From repo root (names only for secrets):

```bash
set -a && . ./.env && set +a
export N8N_HOST_PORT=15679 POSTGRES_HOST_PORT=15433 BACKEND_HOST_PORT=8000 LANGFUSE_TRACING_ENABLED=false

docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend n8n

docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health/ready').status_code)"
docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
```

Ingress smokes: [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md).

---

## 7. Forbidden commands (production)

| Command | Risk |
|---------|------|
| `docker-compose … --force-recreate` | v1 ContainerConfig failure / partial outage |
| `docker run` manual n8n/postgres without compose labels | Split-brain / name conflicts |
| `docker volume rm` on `alpstein_*` | Data loss |
| `docker stop integrationhubspot_n8n` | Breaks unrelated product |
| `docker-compose -p alpstein-n8n up` **while** `alpstein_n8n_compose` on 15679 | Shared `alpstein_n8n_data` corruption |
| Bind dev servers `0.0.0.0:8088` / `8090` on production host | Public static file exposure |

---

## 8. Docker Compose v2 rule

| Use | Do not use |
|-----|------------|
| `docker compose` (v2.40+ on host) | `docker-compose` v1 for **recreate** |
| `docker compose up -d --force-recreate` when needed | `docker-compose up -d --force-recreate` |

See [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md).

---

## 9. Rollback notes

| Failure | Rollback |
|---------|----------|
| Bad unified workflow | Deactivate `aYrRmAGKhP4TJbG9`; restore archived workflows from `n8n/workflows/backups/e1-9-cutover-2026-05-28/` per E1.9 audit |
| Compose stack down | `docker compose … up -d postgres backend n8n` with env exports above |
| Wrong n8n URL profile | Set `BACKEND_BASE_URL=http://backend:8000` in `n8n/.env`; recreate n8n container |

Git tag: `recovery-runtime-stable-2026-05-28`.

---

## 10. Related docs

| Doc | Topic |
|-----|--------|
| [`runtime-surface-hardening.md`](runtime-surface-hardening.md) | OPS-H1 findings and hardening |
| [`operational-ingress-policy.md`](operational-ingress-policy.md) | Single backend ingress |
| [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md) | Production workflow |
| [`postgres-compose.md`](../deployment/postgres-compose.md) | Compose operator commands |
