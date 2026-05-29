# n8n runtime env injection (portable stack)

**Context:** Production n8n is **`alpstein_n8n_compose`** on `127.0.0.1:15679`, often started via **`docker run`** (recovery path), **not** `docker compose`. See [`runtime-map.md`](runtime-map.md).

## Why `docker restart` does not load new env

Environment variables are fixed at **container create** time. Editing `/opt/alpstein-ai/.env` or `n8n/.env` has no effect until the container is **removed and recreated** (or `compose up --force-recreate` on the service that actually owns the container).

## Why `docker compose up` may fail

| Issue | Cause |
|-------|--------|
| `ContainerConfig` / name conflict | `alpstein_n8n_compose` has **no** `com.docker.compose.*` labels — it was not created by the current compose project |
| `f54f1116670d_alpstein_postgres` conflict | Postgres was created with compose project `alpstein-ai` but container name includes compose hash prefix |
| Volume warning `alpstein-n8n` vs `alpstein-ai` | Historical project name on `alpstein_n8n_data` volume |

**Do not** run `docker compose down`. **Do not** delete volumes.

## Canonical env file for n8n

Compose references:

```yaml
env_file:
  - ./n8n/.env
```

ERPNext flags must live in **`/opt/alpstein-ai/n8n/.env`**, not only in repo root `.env`.

```env
ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=true
ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch
```

## Safe fix — Option B (docker run recreate, n8n only)

```bash
# 1. Ensure n8n/.env contains ERPNext vars (names only in docs)
grep -E '^ALPSTEIN_ERPNEXT|^ERPNEXT_BASE' /opt/alpstein-ai/n8n/.env

# 2. Stop/remove ONLY n8n (volume preserved)
docker stop alpstein_n8n_compose
docker rm alpstein_n8n_compose

# 3. Recreate with same volume, network, port, image
docker run -d \
  --name alpstein_n8n_compose \
  --network alpstein_internal \
  --restart unless-stopped \
  -p 127.0.0.1:15679:5678 \
  -v alpstein_n8n_data:/home/node/.n8n \
  --env-file /opt/alpstein-ai/n8n/.env \
  -e BACKEND_BASE_URL=http://backend:8000 \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e WEBHOOK_URL=https://n8n.alpstein-ai.ch/ \
  -e ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=true \
  -e ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch \
  docker.n8n.io/n8nio/n8n:2.22.5

# 4. Publish unified workflow + Telegram webhook recovery
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9
docker restart alpstein_n8n_compose
sleep 20
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9

# 5. Publish while n8n is STOPPED (n8n 2.x; `publish` while running may not persist)
docker stop alpstein_n8n_compose
docker run --rm \
  -v alpstein_n8n_data:/home/node/.n8n \
  --env-file /opt/alpstein-ai/n8n/.env \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  docker.n8n.io/n8nio/n8n:2.22.5 \
  publish:workflow --id=aYrRmAGKhP4TJbG9
docker start alpstein_n8n_compose

# 6. Re-import erpnext_crm_api credential if ERPNext HTTP fails after recreate
```

## Verification

```bash
docker exec alpstein_n8n_compose printenv | grep -E 'ALPSTEIN_ERPNEXT|ERPNEXT_BASE'
curl -sS -o /dev/null -w '%{http_code}\n' -I https://n8n.alpstein-ai.ch/
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:15679/healthz
```

Expected:

```text
ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=true
ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch
```

## Future: align with compose (optional, maintenance window)

When compose recreate is stable on this host, adopt:

```bash
cd /opt/alpstein-ai
export ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=true ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch N8N_HOST_PORT=15679
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --force-recreate n8n
```

Only after resolving postgres container naming / `ContainerConfig` issues documented in [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md).
