# T-b2.7 — n8n on internal compose network

**Status:** Done (2026-05-27)  
**Phase:** B2.7  
**Rollback anchor:** `baseline-b2.6-compose`

## Goal

Portable n8n reaches backend via `BACKEND_BASE_URL=http://backend:8000` on `alpstein_internal` — no host gateway. Live Contabo `alpstein_n8n` untouched.

## Network design

- **Chosen:** `n8n` service in root `docker-compose.yml` on `alpstein_internal` (peer of `backend`).
- **Not chosen:** Separate compose + external network (extra drift).
- Container `alpstein_n8n_compose` — does not replace legacy `alpstein_n8n`.

## Changes

| File | Change |
|------|--------|
| `docker-compose.yml` | `n8n` service, volume `alpstein_n8n_data`, `BACKEND_BASE_URL` override |
| `docker-compose.dev.yml` | `127.0.0.1:15680:5678` (avoids legacy 15679) |
| `n8n/.env.example` | Portable `http://backend:8000` default; legacy `8010` commented |
| `n8n/docker-compose.yml` | Legacy header comment only |
| `docs/deployment/n8n-compose.md` | New runbook |
| `docs/deployment/deployment-contract.md` | B2.7 exit criteria |
| `docs/deployment/README.md` | Index |
| `docs/deployment/postgres-compose.md` | B2.7 pointer |
| `docs/ops/n8n-runtime-start.md` | Portable section |
| `docs/project-status/current-state.md` | B2.7 done |
| `docs/project-status/next-steps.md` | B2.8 next |

## Out of scope

- Live n8n cutover, workflow activation, Telegram, backend code, migrations

## Validation (2026-05-27)

| Check | Result |
|-------|--------|
| `POSTGRES_PASSWORD=… docker-compose -p alpstein-ai config` | Pass |
| `curl` on `alpstein_internal` → `backend:8000/api/v1/health/ready` | Pass (`success: true`) |
| `alpstein_n8n_compose` → `wget http://backend:8000/api/v1/health/ready` | Pass |
| `BACKEND_BASE_URL` inside portable container | `http://backend:8000` |
| Legacy `alpstein_n8n` | Unchanged (still running) |
| Workflow activation / Telegram cutover | Not performed |

Portable n8n stopped after smoke (`docker-compose stop n8n`) to avoid dual-runtime on shared volume.

## Next

**B2.8** — bootstrap profile for clean-clone webhook smoke.
