# T-recovery-1 — Restore runtime source of truth

**Status:** done  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

## Goal

Restore single canonical runtime: `postgres` → `backend` → `n8n` → Telegram / Website Chat after split-brain outage.

## Scope completed

- [x] Pre-flight snapshot (git, docker, networks, `.env` key presence)
- [x] Root `.env` `POSTGRES_*` aligned to portable volume (from running backend)
- [x] Portable postgres started (`alpstein_postgres`, alias `postgres`)
- [x] Backend readiness **200**
- [x] Legacy `alpstein_n8n` stopped; `alpstein_n8n_compose` on **15679**
- [x] `BACKEND_BASE_URL=http://backend:8000`
- [x] Telegram webhook inject smoke **200**
- [x] Website Chat webhook smoke **200**
- [x] Audit: [`docs/audits/recovery-runtime-source-of-truth-2026-05-28.md`](../../docs/audits/recovery-runtime-source-of-truth-2026-05-28.md)

## Out of scope

- Application code changes
- Workflow redesign
- Volume deletion / password rotation
- Stopping legacy `backend_postgres` (operator decision)

## Notes

- `docker-compose up --force-recreate` failed with `ContainerConfig`; postgres/n8n via `docker run` workaround (same as E0).
