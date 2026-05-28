# T-recovery-2 — Compose / recreate stabilization

**Status:** done  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

## Goal

Make portable stack recreation repeatable without manual `docker run` workarounds; eliminate `ContainerConfig` failures on normal ops.

## Completed

- [x] Diagnosed `KeyError: ContainerConfig` — compose v1.29 + Docker 29 recreate path
- [x] Installed `docker-compose-v2`; verified `docker compose` recreate
- [x] Adopted compose-managed containers for postgres, backend, n8n
- [x] Fixed `LANGFUSE_TRACING_ENABLED` compose default
- [x] Documented canonical `docker compose` up path with `N8N_HOST_PORT=15679`
- [x] Smokes: backend ready **200**, Website Chat **200**, Telegram **200**

## Evidence

[`docs/audits/recovery-compose-recreate-stabilization-2026-05-28.md`](../../docs/audits/recovery-compose-recreate-stabilization-2026-05-28.md)

## Out of scope

- Application code
- Volume deletion / DB migration / secret rotation
- Stopping `backend_postgres` (operator)
