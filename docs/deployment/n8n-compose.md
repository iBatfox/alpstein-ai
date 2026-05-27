# n8n compose network integration (B2.7)

**Contract:** [`deployment-contract.md`](deployment-contract.md) §8  
**Compose:** [`docker-compose.yml`](../../docker-compose.yml) service `n8n` on `alpstein_internal`  
**Legacy host n8n:** [`n8n/docker-compose.yml`](../../n8n/docker-compose.yml) — **unchanged on Contabo**

---

## Network design

**Choice:** n8n joins the **root** `docker-compose.yml` as peer service `n8n` on network `alpstein_internal` (same pattern as `backend`).

| Approach | Rollback | Chosen |
|----------|----------|--------|
| Service in root compose | `docker-compose down`; revert compose commit | **Yes** |
| Separate compose + `external: alpstein_internal` | Two files; drift risk | No (extra moving parts) |

```text
alpstein_internal
  postgres:5432 ← backend:8000 ← n8n:5678
```

| Consumer | URL |
|----------|-----|
| n8n → backend | `http://backend:8000` (`BACKEND_BASE_URL`) |
| Readiness probe | `GET http://backend:8000/api/v1/health/ready` |
| Webhook (workflows) | `POST http://backend:8000/api/v1/webhook/message` |

**No** `172.20.0.1:8010`, **no** `extra_hosts: host-gateway` in portable path.

---

## Service summary

| Attribute | Portable (`docker-compose.yml`) | Legacy (`n8n/docker-compose.yml`) |
|-----------|--------------------------------|-----------------------------------|
| Service / container | `n8n` / `alpstein_n8n_compose` | `alpstein_n8n` / `alpstein_n8n` |
| Compose project | `alpstein-ai` (repo root) | `alpstein-n8n` (`n8n/` dir) |
| Backend URL | `http://backend:8000` | `http://172.20.0.1:8010` |
| Host port (default) | none | `127.0.0.1:15679` |
| Host port (dev overlay) | `127.0.0.1:15680` | — |
| Volume | `alpstein_n8n_data` | `alpstein_n8n_data` |
| `depends_on` | `backend` healthy | — |

**Live Contabo:** keep running `alpstein_n8n` via legacy compose — **do not** start portable `n8n` on the same host until cutover plan (volume + port conflict).

---

## Environment

Copy [`n8n/.env.example`](../../n8n/.env.example) → `n8n/.env`.

| Variable | Portable value | Notes |
|----------|----------------|-------|
| `BACKEND_BASE_URL` | `http://backend:8000` | Compose also sets `environment:` override |
| `N8N_BACKEND_API_TOKEN` | Same as root/backend `.env` | Header `X-Alpstein-Webhook-Token` |
| `N8N_ENCRYPTION_KEY` | Stable per volume | Required |
| `N8N_BASIC_AUTH_*` | Operator-set | Admin UI |

Root compose passes `env_file: ./n8n/.env` and **overrides** `BACKEND_BASE_URL` to `http://backend:8000` so legacy values in an existing `.env` do not break portable stack.

---

## Commands

### Validate compose (no start)

```bash
cd /opt/alpstein-ai
docker-compose -p alpstein-ai config
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config
```

### Portable stack (clean clone / dev)

```bash
cd /opt/alpstein-ai
# .env at repo root + n8n/.env + backend/.env per templates
docker-compose -p alpstein-ai up -d postgres backend
docker-compose -p alpstein-ai up -d n8n
```

Dev UI on host: add overlay and open `http://127.0.0.1:15680` (not `15679` — legacy).

```bash
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Connectivity check (from n8n container)

```bash
docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
```

Expect JSON with `"success": true` — no tokens in output.

### Ephemeral check (without starting n8n)

```bash
docker run --rm --network alpstein_internal curlimages/curl:8.5.0 -sf \
  http://backend:8000/api/v1/health/ready
```

---

## Rollback (RBU)

| Target | Action |
|--------|--------|
| `baseline-b2.6-compose` | Revert compose commit; `docker-compose -p alpstein-ai down`; legacy n8n unchanged |
| Live Contabo | Continue `cd n8n && docker-compose -p alpstein-n8n up -d` only |

**Do not** import workflows, activate Telegram, or change credentials as part of B2.7.

---

## B2.8 drift (remaining)

- Bootstrap profile (seed + demo SQL) for webhook smoke on fresh DB
- Clean-clone gate transcript (B2.9)
- Optional: cutover runbook from legacy `alpstein_n8n` → `alpstein_n8n_compose` (volume rebind, Telegram webhook re-register)

---

## Related

| Doc | Topic |
|-----|--------|
| [`postgres-compose.md`](postgres-compose.md) | Postgres + backend |
| [`n8n-runtime-start.md`](../ops/n8n-runtime-start.md) | Legacy host runbook |
| [`n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md) | Token alignment |
