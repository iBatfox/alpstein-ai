# RECOVERY-1 — Runtime source of truth restoration

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Operator:** agent (controlled recovery)  
**Task:** [`tasks/done/T-recovery-1-runtime-source-of-truth.md`](../../tasks/done/T-recovery-1-runtime-source-of-truth.md)  
**Prior diagnosis:** runtime split-brain (portable postgres stopped; legacy n8n on dead `:8010`)

## Final verdict

| Verdict | **PASS WITH NOTES** |
|---------|---------------------|

---

## 1. Topology restored

```text
alpstein_internal
  alpstein_postgres (network alias: postgres) :5432
       ↑
  alpstein_backend :8000
       ↑
  alpstein_n8n_compose @ 127.0.0.1:15679 (nginx production upstream)
       BACKEND_BASE_URL=http://backend:8000
```

| Component | State |
|-----------|--------|
| Portable postgres | **Running** — `alpstein_postgres`, volume `alpstein_postgres_data`, dev bind `127.0.0.1:15433` |
| Portable backend | **Running healthy** — `alpstein_backend`, readiness **200** |
| Portable n8n | **Running** — `alpstein_n8n_compose` on **15679** (single owner) |
| Legacy `alpstein_n8n` | **Stopped** (not on 15679) |
| Legacy `backend_postgres` | **Still running** on `127.0.0.1:15432` — **not** in active chain (isolation note) |

---

## 2. Pre-flight (snapshot)

| Check | Result |
|-------|--------|
| Git | Dirty docs/widget paths; branch `stabilization/runtime-baseline` |
| Root `.env` before fix | `POSTGRES_*` **missing**; `N8N_BACKEND_API_TOKEN` set |
| Exited portable postgres | `195f013f5404_alpstein_postgres` / ghost after failed compose recreate |
| Backend | Unhealthy, `DATABASE_ERROR` |

---

## 3. Recovery actions (executed)

| Step | Action | Result |
|------|--------|--------|
| `.env` | Synced `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` from running `alpstein_backend` env (volume-aligned; values not logged) | **OK** |
| Postgres | `docker run` with `--network-alias postgres` on `alpstein_internal` (compose `up` recreate hit `ContainerConfig` on this host) | **OK** |
| Backend | `docker restart alpstein_backend` after postgres healthy | Readiness **200** |
| n8n | Stopped legacy `alpstein_n8n`; started `alpstein_n8n_compose` via `docker run` on **15679** per E0 workaround | **OK** |
| `n8n/.env` | `BACKEND_BASE_URL` → `http://backend:8000` | **OK** |

**Not executed:** volume delete, password rotation, Alembic migrate, legacy `backend_postgres` stop, `docker-compose up` full stack (blocked by v1.29 + Docker 29 `KeyError: 'ContainerConfig'` on recreate).

---

## 4. Verification

### Backend readiness

| Probe | Result |
|-------|--------|
| In-container `GET /api/v1/health/ready` | **200** — `db: reachable` |
| `docker inspect` health | **healthy** |

### n8n → backend

| Probe | Result |
|-------|--------|
| `wget http://backend:8000/api/v1/health/ready` from `alpstein_n8n_compose` | **200** |
| Legacy `172.20.0.1:8010` | **Not used** |

### Telegram smoke (webhook inject)

| Field | Value |
|-------|--------|
| URL | `http://127.0.0.1:15679/webhook/alpstein-telegram-customer-trigger/webhook` |
| HTTP | **200** |
| Backend log | `POST /api/v1/webhook/message` **200** from `172.21.0.4` (n8n) |
| POST Backend timeout | **None** (~0.5s) |

### Website Chat smoke

| Field | Value |
|-------|--------|
| URL | `http://127.0.0.1:15679/webhook/alpstein/website-chat/incoming` |
| HTTP | **200** |
| Body | `success: true`, `reply` text present |
| `correlation_id` | `eafe83db-8b22-41d6-ace4-ae34b8337641` |
| POST Backend timeout | **None** (~3.7s) |

---

## 5. Remaining risks / follow-ups

| Risk | Severity | Mitigation |
|------|----------|------------|
| `docker-compose up --force-recreate` **ContainerConfig** on this host | High for automation | Keep E0 `docker run` workarounds or upgrade compose/Engine |
| Dual Postgres containers (`alpstein_postgres` + `backend_postgres`) | Medium (confusion) | Operator may stop legacy DB when portable SoT accepted; **do not delete volumes** |
| Root `.env` still has stale `ALPSTEIN_AI_DATABASE_URL=...@localhost` line | Low | Align or remove; compose uses `POSTGRES_*` interpolation |
| Backend host port **8000** not mapped (no dev overlay on running container) | Low | Use `docker exec` or recreate with `docker-compose.dev.yml` when compose works |
| n8n execution IDs | Low | Query n8n UI for post-recovery runs; sqlite CLI unavailable in image |
| HubSpot n8n | — | **Untouched** |

---

## 6. Operator commands (reference — already run)

See E0 remediation [`e0-telegram-reference-channel-remediation-2026-05-28.md`](e0-telegram-reference-channel-remediation-2026-05-28.md) for portable `docker run` n8n pattern. Postgres pattern: `docker run --name alpstein_postgres --network alpstein_internal --network-alias postgres …`.

---

## 7. Files touched (recovery)

| File | Change |
|------|--------|
| `.env` (root) | Added `POSTGRES_*` — **do not commit** |
| `n8n/.env` | `BACKEND_BASE_URL` portable value — **do not commit** |
| This audit + project-status + task | Documentation |
