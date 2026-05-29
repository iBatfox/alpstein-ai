# F.1.1 ERPNext Production Deployment Report

**Date:** 2026-05-29  
**Server:** `144.91.113.184`  
**Public URL:** `https://crm.alpstein-ai.ch`  
**Project path:** `/opt/alpstein-erpnext`  
**Compose project:** `alpstein-erpnext`  
**Branch:** `stabilization/runtime-baseline`

## Scope

Isolated ERPNext install via official `frappe_docker`. No Alpstein integration, no CRM sync, no PostgreSQL coupling.

## Deployment Summary

### Stack

| Component | Image / version |
|-----------|-----------------|
| ERPNext / Frappe | `frappe/erpnext:v15.69.2` |
| MariaDB | `mariadb:10.6` (256M InnoDB buffer pool) |
| Redis cache | `redis:8.6-alpine` (128M maxmemory) |
| Redis queue | `redis:8.6-alpine` (128M maxmemory) |
| frappe_docker source | `main` (clone; tag `v5.24.0` not found upstream) |

### Containers started

| Container | Role |
|-----------|------|
| `alpstein-erpnext-frontend-1` | nginx entrypoint → loopback publish |
| `alpstein-erpnext-backend-1` | Gunicorn (1 worker, 2 threads) |
| `alpstein-erpnext-websocket-1` | Socket.IO |
| `alpstein-erpnext-scheduler-1` | `bench schedule` |
| `alpstein-erpnext-queue-short-1` | RQ worker (short/default) |
| `alpstein-erpnext-queue-long-1` | RQ worker (long/default/short) |
| `alpstein-erpnext-db-1` | MariaDB |
| `alpstein-erpnext-redis-cache-1` | Redis cache |
| `alpstein-erpnext-redis-queue-1` | Redis queue |

Site: `crm.alpstein-ai.ch` (Frappe site name matches hostname).

### Published ports (host)

| Bind | Service | Notes |
|------|---------|-------|
| `127.0.0.1:18080→8080` | ERPNext frontend | **Only** ERPNext host publish |
| — | MariaDB 3306 | Internal only |
| — | Redis 6379 | Internal only |
| — | Gunicorn 8000 | Internal only |

**Important:** Do **not** include `overrides/compose.noproxy.yaml` in `COMPOSE_FILE` — it adds `0.0.0.0:8080` alongside loopback.

### Docker network

- `alpstein-erpnext_default` (bridge) — ERPNext stack only
- **Not** attached to `alpstein_internal` or `alpstein-n8n_default`

### Volumes

| Volume | Purpose |
|--------|---------|
| `alpstein-erpnext_sites` | Bench sites, assets, config |
| `alpstein-erpnext_db-data` | MariaDB data |
| `alpstein-erpnext_redis-queue-data` | Redis queue persistence |

### Secrets / config (host, not in git)

- `/etc/alpstein/erpnext.env` — site name, version pins, DB/admin passwords, Gunicorn tuning
- `/opt/alpstein-erpnext/.env` — copy for compose (mode 600)
- `/opt/alpstein-erpnext/compose.alpstein.override.yaml` — loopback port, low-memory MariaDB/Redis, memory limits

### TLS / nginx

- Vhost: `/etc/nginx/sites-available/crm.alpstein-ai.ch`
- Let's Encrypt cert issued 2026-05-29; expires **2026-08-27**
- HTTP → HTTPS redirect via certbot

### Compose command (canonical)

```bash
cd /opt/alpstein-erpnext
export COMPOSE_FILE="compose.yaml:overrides/compose.mariadb.yaml:overrides/compose.redis.yaml:compose.alpstein.override.yaml"
set -a && source /etc/alpstein/erpnext.env && set +a
docker compose -p alpstein-erpnext up -d
```

---

## Verification Results

### `docker ps` (ERPNext)

```
alpstein-erpnext-frontend-1      Up   127.0.0.1:18080->8080/tcp
alpstein-erpnext-backend-1       Up
alpstein-erpnext-db-1            Up (healthy)   3306/tcp
alpstein-erpnext-redis-cache-1   Up             6379/tcp
alpstein-erpnext-redis-queue-1   Up             6379/tcp
alpstein-erpnext-scheduler-1     Up
alpstein-erpnext-queue-short-1   Up
alpstein-erpnext-queue-long-1    Up
alpstein-erpnext-websocket-1     Up
```

### Networks

```
alpstein-erpnext_default   bridge
```

(Alpstein networks unchanged: `alpstein_internal`, `alpstein-n8n_default`.)

### Volumes

```
alpstein-erpnext_db-data
alpstein-erpnext_redis-queue-data
alpstein-erpnext_sites
```

### HTTP / HTTPS

| Check | Result |
|-------|--------|
| `curl http://127.0.0.1:18080/` | **200** (login page) |
| `curl -I http://crm.alpstein-ai.ch/` | **301** → HTTPS |
| `curl -I https://crm.alpstein-ai.ch/` | **200** (login page) |
| `http://144.91.113.184:8080` | **blocked** (connection refused) |
| `http://144.91.113.184:8000` | **blocked** |
| `http://144.91.113.184:18080` | **blocked** |
| DNS `crm.alpstein-ai.ch` | **144.91.113.184** |

### Alpstein regression (unchanged)

| Service | Health |
|---------|--------|
| `alpstein_backend` @ `127.0.0.1:8000` | **200** `/api/v1/health` |
| `alpstein_n8n_compose` @ `127.0.0.1:15679` | **200** `/healthz` |
| `alpstein_postgres` @ `127.0.0.1:15433` | healthy |
| `integrationhubspot_n8n` @ `127.0.0.1:15678` | Up (untouched) |

---

## Health Report

| Component | Status | Evidence |
|-----------|--------|----------|
| ERPNext web | **OK** | HTTPS 200, `X-Page-Name: login` |
| nginx routing | **OK** | Host nginx → `127.0.0.1:18080` |
| TLS | **OK** | Let's Encrypt deployed |
| MariaDB | **OK** | `healthy`; site + erpnext installed |
| Redis cache | **OK** | `PONG` |
| Redis queue | **OK** | `PONG` |
| Scheduler | **OK** | container Up |
| Workers | **OK** | queue-short + queue-long Up |

Administrator password: stored in `/etc/alpstein/erpnext.env` (`ADMIN_PASSWORD`).

---

## Reviewer Findings (deployment)

### HIGH

| Risk | Mitigation |
|------|------------|
| **Shared 5.8 GB RAM** with Alpstein AI — ERPNext + MariaDB + workers can trigger OOM under load or during `bench migrate` / reports | Keep Gunicorn at 1 worker; MariaDB buffer 256M; monitor `free -h` and `dmesg \| grep -i oom`; plan RAM upgrade to 12–16 GB before heavy CRM use |
| **Accidental public 8080** if `compose.noproxy.yaml` is added to `COMPOSE_FILE` | Documented in override header; use only `compose.alpstein.override.yaml` for port publish |

### MEDIUM

| Risk | Mitigation |
|------|------------|
| **frappe_docker not pinned** to release tag (v5.24.0 missing) | Pin commit SHA or valid release tag in runbook after operator review |
| **No first backup recorded** yet | Run F.1.9 backup script; schedule daily cron |
| **Upgrade path** requires image pull + `bench migrate` downtime | Follow runbook F.1.10; backup before every upgrade |

### LOW

| Risk | Mitigation |
|------|------------|
| Cert renewal | certbot timer; `certbot renew --dry-run` quarterly |
| Docker memory limits on workers may restart jobs under spike | Accept for MVP; increase limits if job failures appear in logs |
| Single-node ERPNext — no HA | Expected for F.1.1 scope |

---

## Operator follow-up

- [ ] Log in at `https://crm.alpstein-ai.ch` as `Administrator` (password in `/etc/alpstein/erpnext.env`)
- [ ] Run first backup per `docs/ops/erpnext-production-deployment-runbook.md` § F.1.9
- [ ] Optional: `ufw deny 18080/tcp` (defense in depth; loopback bind already enforced)
- [ ] Archivist: sync project-status after human acceptance

---

## Files created / modified (host)

| Path | Action |
|------|--------|
| `/opt/alpstein-erpnext/` | frappe_docker clone + override |
| `/etc/alpstein/erpnext.env` | secrets (600) |
| `/etc/nginx/sites-available/crm.alpstein-ai.ch` | nginx + certbot |
| `/etc/letsencrypt/live/crm.alpstein-ai.ch/` | TLS cert |

**Alpstein AI repo:** this audit doc + runbook evidence update only.
