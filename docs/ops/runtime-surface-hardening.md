# OPS-H1 — Runtime surface cleanup & port hardening

**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**  
**Task:** [`tasks/done/T-ops-h1-runtime-surface-cleanup-port-hardening.md`](../../tasks/done/T-ops-h1-runtime-surface-cleanup-port-hardening.md)  
**Runtime map:** [`runtime-map.md`](runtime-map.md)

---

## 1. Objective

Reduce operator confusion and accidental exposure **without** destructive cleanup or production ingress changes.

---

## 2. Runtime inventory (2026-05-28)

### Canonical (active)

| Asset | State |
|-------|--------|
| `alpstein_postgres` | Up, healthy, `127.0.0.1:15433` |
| `alpstein_backend` | Up, healthy, `127.0.0.1:8000` |
| `alpstein_n8n_compose` | Up, `127.0.0.1:15679` |
| Workflow `alpstein-customer-ingress` | Production (E1.9) |
| Network `alpstein_internal` | Active |
| Volumes `alpstein_postgres_data`, `alpstein_n8n_data` | In use |

### Legacy (deprecated / absent)

| Asset | State (inventory) |
|-------|-------------------|
| `backend_postgres` | **Not running** (no `15432` listener) |
| `alpstein_n8n` (legacy) | **Not running** |
| Host uvicorn `:8010` | **No listener** |
| Archived workflows `2lMuaSWD1XFOXLEK`, `hAJ3TFYn69in0vd5` | Inactive per E1.9 |

### Foreign (do not touch)

| Asset | State |
|-------|--------|
| `integrationhubspot_n8n` | Up, `127.0.0.1:15678` |

### Dev / unsafe surfaces found

| Surface | Bind | Risk |
|---------|------|------|
| `python3 -m http.server` | **`0.0.0.0:8088`** (multiple PIDs) | Public static file server |
| `python3 -m http.server` | **`0.0.0.0:8090`** | Same |
| Host PostgreSQL | `127.0.0.1:5432` | Unrelated to Alpstein portable DB — do not confuse with `15433` |

---

## 3. nginx upstream (verified)

File: `/etc/nginx/sites-available/n8n.alpstein-ai.ch`

```text
server_name n8n.alpstein-ai.ch;
proxy_pass http://127.0.0.1:15679;
```

HubSpot remains on `n8n.conf` → **15678** (separate vhost).

---

## 4. Hardening actions applied

| Action | Applied? | Notes |
|--------|----------|--------|
| Created [`runtime-map.md`](runtime-map.md) | **Yes** | Canonical port / topology reference |
| Created this audit | **Yes** | OPS-H1 evidence |
| Updated [`README.md`](README.md) | **Yes** | Links to runtime map |
| Updated project-status | **Yes** | OPS-H1 row |
| Stopped `0.0.0.0` http.server | **No** | Avoid breaking in-flight widget tests; operator procedure documented |
| Removed legacy containers/volumes | **No** | Out of scope (non-destructive) |
| Firewall / nginx changes | **No** | Out of scope |

### Recommended dev static server procedure

From repo root (widget / example HTML):

```bash
cd /opt/alpstein-ai/website-widget
python3 -m http.server 18080 --bind 127.0.0.1
```

For temporary ports **8088** / **8090**, always use `--bind 127.0.0.1`.  
To stop accidental public listeners:

```bash
ss -ltnp | grep -E ':8088|:8090'
# kill only confirmed stale PIDs; prefer fuser -k 8088/tcp after operator confirmation
```

---

## 5. Validation (post-inventory)

| Check | Result |
|-------|--------|
| Backend readiness | **200** |
| n8n → backend ready | **200** |
| Unified Website Chat webhook (`15679`) | **200** |
| Unified Telegram webhook inject | **403** (secret/header probe — live DM not re-run in OPS-H1) |
| Legacy `8010` / `15432` | **No listeners** |
| Postgres public exposure | **None** (`15433` loopback only) |
| Duplicate n8n on 15679 | **None** |

**Operator follow-up:** Confirm live Telegram DM to customer bot (post E1.9).

---

## 6. Remaining risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `0.0.0.0:8088` / `8090` http.server | **High** if host has public IP | Operator stop + localhost bind |
| Stale docs referencing `15680`, `8010`, `15432` | Medium | Prefer `runtime-map.md`; update runbooks incrementally |
| `docker-compose` v1 still on PATH | Medium | Use `docker compose` only |
| `backend_postgres_data` volume orphaned | Low | Mark deprecated; no delete without backup policy |
| Multiple duplicate `http.server` PIDs on 8088 | Low | Clean stale processes when safe |

---

## 7. Recommended future cleanup (operator, non-urgent)

1. Stop and document removal of **`0.0.0.0`** dev http.server processes when widget testing idle.
2. **`docker rm`** stopped legacy containers only after 30-day confirmation (`backend_postgres` if recreated, old `alpstein_n8n` ghosts) — **never** `volume rm`.
3. Archive ops docs that still list legacy `alpstein_n8n` as “production path today” ([`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md)).
4. Align Website Chat runbook port examples to **15679** + unified webhook path only.

---

## 8. Files changed

| File |
|------|
| `docs/ops/runtime-map.md` (new) |
| `docs/ops/runtime-surface-hardening.md` (new) |
| `docs/ops/README.md` |
| `docs/project-status/current-state.md` |
| `docs/project-status/next-steps.md` |
| `tasks/done/T-ops-h1-runtime-surface-cleanup-port-hardening.md` (new) |
