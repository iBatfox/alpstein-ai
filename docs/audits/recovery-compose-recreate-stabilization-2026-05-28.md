# RECOVERY-2 — Compose / recreate stabilization

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Task:** [`tasks/done/T-recovery-2-compose-recreate-stabilization.md`](../../tasks/done/T-recovery-2-compose-recreate-stabilization.md)  
**Prior:** [`recovery-runtime-source-of-truth-2026-05-28.md`](recovery-runtime-source-of-truth-2026-05-28.md) (RECOVERY-1)

## Final verdict

| Verdict | **PASS WITH NOTES** |
|---------|---------------------|

---

## 1. Root cause — `KeyError: 'ContainerConfig'`

| Factor | Evidence |
|--------|----------|
| **Primary** | **docker-compose v1.29.2** (Python, EOL) calls `container.image_config['ContainerConfig']` during **recreate** volume merge — field removed in **Docker Engine 29** image inspect API |
| **Trigger** | `docker-compose up -d --force-recreate` or any convergence path that **recreates** an existing container |
| **Not the cause** | Wrong `docker-compose.yml` schema, missing `POSTGRES_PASSWORD`, or corrupt volumes |
| **Contributing** | RECOVERY-1 **`docker run`** containers lacked `com.docker.compose.*` labels → name conflicts on `docker-compose up` |
| **Secondary startup failure** | Empty `LANGFUSE_TRACING_ENABLED` interpolated into backend env → Pydantic bool parse error on fresh compose backend |

**Versions (host):**

| Tool | Version |
|------|---------|
| `docker-compose` (v1) | 1.29.2 |
| `docker compose` (v2) | **2.40.3** (installed during RECOVERY-2 via `docker-compose-v2` package) |
| Docker Engine | 29.1.3 |

---

## 2. Stabilization applied

| Action | Result |
|--------|--------|
| Installed **`docker-compose-v2`** (`docker compose` plugin) | **OK** |
| Adopted stack via **create path**: `docker rm` manual containers → `docker-compose up -d` (v1) for postgres/backend | **OK** |
| Fixed `LANGFUSE_TRACING_ENABLED` default → `false` in `docker-compose.yml` | **OK** |
| Full stack via **`docker compose` v2** with dev overlay + `N8N_HOST_PORT=15679` | **OK** |
| Verified **`docker compose up -d --force-recreate --no-deps backend`** | **OK** (readiness **200**) |
| Documented v1 ban on `--force-recreate` | `.env.example`, `postgres-compose.md` |

---

## 3. Verified compose path (canonical)

```bash
cd /opt/alpstein-ai
set -a && . ./.env && set +a
export N8N_HOST_PORT=15679
export POSTGRES_HOST_PORT=15433
export BACKEND_HOST_PORT=8000
export LANGFUSE_TRACING_ENABLED=false

docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend n8n
```

| Service | Container | Network DNS |
|---------|-----------|-------------|
| `postgres` | `alpstein_postgres` | `postgres` |
| `backend` | `alpstein_backend` | `backend` |
| `n8n` | `alpstein_n8n_compose` | `backend:8000` |

All containers carry `com.docker.compose.project=alpstein-ai`.

---

## 4. v1 vs v2 behavior

| Command | Result |
|---------|--------|
| `docker-compose … up -d` (create, after `docker rm`) | **Works** |
| `docker-compose … up -d --force-recreate` | **Fails** — `KeyError: 'ContainerConfig'` |
| `docker compose … up -d` | **Works** |
| `docker compose … up -d --force-recreate` | **Works** |

**Operator rule:** On this host, use **`docker compose`** (v2) for routine ops and recreates. Reserve hyphenated **`docker-compose`** only if v2 unavailable — never with `--force-recreate`.

---

## 5. Verification (post-stabilization)

| Check | Result |
|-------|--------|
| `docker compose config` | **PASS** — services `postgres`, `backend`, `n8n` |
| Postgres healthy | **PASS** — `pg_isready` |
| Backend `/api/v1/health/ready` | **200** (container + host `127.0.0.1:8000`) |
| n8n → backend ready | **200** |
| Website Chat webhook `15679` | **200** |
| Telegram webhook inject `15679` | **200** |
| Single n8n on **15679** | `alpstein_n8n_compose` only |
| Legacy `alpstein_n8n` | **Removed** (not running) |
| Legacy `backend_postgres` | **Still up** on `15432` — isolated, not in chain |

---

## 6. Remaining risks

| Risk | Notes |
|------|--------|
| Dual Compose CLIs on host | Scripts/docs must prefer `docker compose`; v1 footgun remains installed |
| `version:` key in YAML | v2 warns obsolete — cosmetic |
| Legacy `backend_postgres` | Operator may stop after backup confirmation |
| HubSpot n8n | **Untouched** (`15678`) |
| `.env` / `n8n/.env` | Not committed; must keep `POSTGRES_*` + port exports |

---

## 7. Files changed

| File | Change |
|------|--------|
| `docker-compose.yml` | `LANGFUSE_TRACING_ENABLED` default `false` |
| `.env.example` | Compose v2 note, `N8N_HOST_PORT`, `LANGFUSE_TRACING_ENABLED` |
| `docs/deployment/postgres-compose.md` | Operator commands + troubleshooting |
| `docs/audits/recovery-compose-recreate-stabilization-2026-05-28.md` | This audit |
| `docs/project-status/current-state.md` | RECOVERY-2 summary |
| `docs/project-status/next-steps.md` | Updated queue |
| `tasks/done/T-recovery-2-compose-recreate-stabilization.md` | Task closure |
