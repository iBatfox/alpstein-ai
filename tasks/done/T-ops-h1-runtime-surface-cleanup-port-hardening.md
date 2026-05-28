# T-ops-h1 — Runtime surface cleanup & port hardening

**Status:** done  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

## Goal

Inventory runtime surface, classify ports, document canonical map, reduce ambiguity without destructive cleanup.

## Completed

- [x] Runtime inventory (docker, networks, volumes, `ss`, nginx)
- [x] Port classification table in [`docs/ops/runtime-map.md`](../../docs/ops/runtime-map.md)
- [x] Legacy review: `backend_postgres`, `alpstein_n8n`, `8010`, `15432` — not active
- [x] Unsafe surfaces documented: `0.0.0.0:8088`, `8090` http.server
- [x] Validation: backend **200**, n8n→backend **200**, unified Website Chat **200**
- [x] OPS audit [`docs/ops/runtime-surface-hardening.md`](../../docs/ops/runtime-surface-hardening.md)

## Not applied (by design)

- Stopping public http.server (avoid breaking active tests)
- Volume/container deletion
- nginx / firewall / compose changes

## Evidence

[`docs/ops/runtime-surface-hardening.md`](../../docs/ops/runtime-surface-hardening.md)
