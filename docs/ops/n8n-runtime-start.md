**Doc status:** runtime-derived  
**Tier:** ops/production (pending move)

# Alpstein n8n — Runtime Start (T13.0-impl)

**Compose:** [`n8n/docker-compose.yml`](../../n8n/docker-compose.yml)  
**Deployment plan:** [`n8n-deployment-plan.md`](n8n-deployment-plan.md)  
**Env checklist:** [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md)

Project-local n8n for Alpstein AI T13 workflows. **Separate** from HubSpot n8n — see warning below.

**CLI note:** This server uses **docker-compose v1.29** — use `docker-compose` (hyphen), not `docker compose`.

---

## Warning — do not touch HubSpot n8n

This server may run **`integrationhubspot_n8n`** on `127.0.0.1:15678`.

| Do | Do not |
|----|--------|
| Use compose project **`alpstein-n8n`** | Stop/remove/edit `integrationhubspot_n8n` |
| Use container **`alpstein_n8n`** on port **15679** | Reuse HubSpot volumes or `.env` |
| Run commands from `/opt/alpstein-ai/n8n/` | Run `docker-compose down` in HubSpot project dirs |

Before first start, confirm HubSpot n8n is still up:

```bash
docker ps --filter name=integrationhubspot_n8n
ss -tlnp | grep -E '15678|15679'
```

---

## Warning — `BACKEND_BASE_URL` inside the container

From inside **`alpstein_n8n`**, `127.0.0.1` is the **container**, not the host.

| Wrong (inside container) | Correct (this server) |
|--------------------------|-------------------------|
| `http://127.0.0.1:8010` | `http://172.20.0.1:8010` (compose network gateway) |
| `http://172.17.0.1:8010` | Wrong bridge — Alpstein uses `alpstein-n8n_default` (`172.20.0.0/16`) |

Set in `/opt/alpstein-ai/n8n/.env`. Requires **UFW** allow from `172.20.0.0/16` → host `tcp/8010` (see below).

### UFW (Alpstein n8n → host backend)

```bash
sudo ufw allow from 172.20.0.0/16 to any port 8010 proto tcp comment 'alpstein-n8n to host backend 8010'
```

Does **not** open port 8010 to the public internet — only the `alpstein-n8n_default` Docker subnet.

**Backend bind:** host process must listen on **`0.0.0.0:8010`** (not `127.0.0.1` only) so the gateway IP `172.20.0.1` can reach it from the container.

Verify from container:

```bash
docker exec alpstein_n8n wget -qO- http://172.20.0.1:8010/api/v1/health
```

---

## One-time setup

1. Copy env template:

```bash
cd /opt/alpstein-ai/n8n
cp .env.example .env
```

2. Edit `/opt/alpstein-ai/n8n/.env`:

| Variable | Required |
|----------|----------|
| `N8N_ENCRYPTION_KEY` | Yes — `openssl rand -hex 32` |
| `N8N_BASIC_AUTH_USER` | Yes |
| `N8N_BASIC_AUTH_PASSWORD` | Yes |
| `BACKEND_BASE_URL` | Yes — `http://172.20.0.1:8010` (gateway for `alpstein-n8n_default`; **not** `127.0.0.1`) |
| `N8N_BACKEND_API_TOKEN` | Yes — must match backend `.env` |

3. Validate compose (no start):

```bash
cd /opt/alpstein-ai/n8n
docker-compose -p alpstein-n8n config
```

4. **Review** compose + `.env` with team before first `up`.

---

## Start / stop / logs

Working directory: `/opt/alpstein-ai/n8n`

### Start

```bash
cd /opt/alpstein-ai/n8n
docker-compose -p alpstein-n8n up -d
```

### Stop (Alpstein only)

```bash
cd /opt/alpstein-ai/n8n
docker-compose -p alpstein-n8n stop
```

### Stop and remove container (keeps volume)

```bash
cd /opt/alpstein-ai/n8n
docker-compose -p alpstein-n8n down
```

### Logs

```bash
docker-compose -p alpstein-n8n logs -f alpstein_n8n
```

### Status

```bash
docker-compose -p alpstein-n8n ps
docker ps --filter name=alpstein_n8n
```

---

## Access

| Item | URL |
|------|-----|
| n8n UI | `http://127.0.0.1:15679` |
| Test webhook (after import + listen) | `http://127.0.0.1:15679/webhook-test/alpstein/test/incoming` |

Login with `N8N_BASIC_AUTH_*` from `.env`.

---

## Workflow import (manual — not automated)

1. Open n8n UI.
2. Import from file: `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`.
3. See [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md).

No auto-import on container start (MVP).

---

## Manual verification checklist

Run **after** `docker-compose -p alpstein-n8n up -d` (operator — not part of T13.0-impl commit).

### Isolation

- [ ] `docker ps` shows `alpstein_n8n` **Up**.
- [ ] `integrationhubspot_n8n` still **Up** (unchanged).
- [ ] Port **15679** bound to `127.0.0.1` only; **15678** still HubSpot.

### n8n health

- [ ] `http://127.0.0.1:15679` prompts basic auth.
- [ ] Login succeeds.
- [ ] Restart test: `docker-compose -p alpstein-n8n restart alpstein_n8n` — data persists on volume `alpstein_n8n_data`.

### Environment

- [ ] `N8N_ENCRYPTION_KEY` was set **before** first start.
- [x] `BACKEND_BASE_URL=http://172.20.0.1:8010` (compose gateway — **not** `127.0.0.1` inside container).
- [x] UFW allows `172.20.0.0/16` → host `tcp/8010`.
- [x] Backend listens on `0.0.0.0:8010`.
- [ ] Workflow can read `$env.BACKEND_BASE_URL` and `$env.N8N_BACKEND_API_TOKEN` (after import).

### Backend (Gate 1)

- [x] Import workflow + POST test payload → `success: true` + `reply_to_customer` ([`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) — **Gate 1 passed** 2026-05-25).

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| Backend unreachable from n8n | `BACKEND_BASE_URL=http://172.20.0.1:8010`; UFW: `allow from 172.20.0.0/16 to port 8010` |
| 401 from backend | Align `N8N_BACKEND_API_TOKEN` with backend `.env` |
| Port in use | `ss -tlnp \| grep 15679` — must not conflict with 15678 |
| Credentials corrupted | Wrong `N8N_ENCRYPTION_KEY` vs volume — restore backup or reset volume (data loss) |

---

## Volume

| Name | Mount |
|------|--------|
| `alpstein_n8n_data` | `/home/node/.n8n` |

List: `docker volume inspect alpstein_n8n_data`
