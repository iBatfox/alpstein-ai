**Doc status:** canonical (ops)  
**Tier:** ops/production  
**As-of:** 2026-05-27 (D4.5 / OPS-C1)  
**Canonical anchor:** [`deployment-contract.md`](../deployment/deployment-contract.md) · [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md)

# Operational ingress policy

Single source of truth for **which backend process** receives n8n and operator traffic after Phase D4.

---

## Policy (mandatory)

| Environment profile | Backend URL | When to use |
|---------------------|---------------|-------------|
| **Portable compose (default for verification)** | `http://backend:8000` | D4-verified path; migrate-then-serve; readiness probe |
| **Legacy Contabo host** | `http://172.20.0.1:8010` | Documented compatibility only; **not** default for CIP/D4 validation |
| **Dev overlay (host curl)** | `http://127.0.0.1:8000` | Local operator curls to mapped compose port |

**Rule:** Exactly **one** active backend ingress per n8n instance. Never point one n8n at compose and host backends interchangeably without a documented cutover.

---

## OPS-C1 — stale host process (mitigated)

**Problem (D4.1):** A long-running host uvicorn on `127.0.0.1:8010` served **pre-baseline** code while compose ran current behavior — observability and correlation checks failed on the wrong process.

**Mitigation:**

1. Route operational tests and new work through **compose** (`alpstein_backend`), **or**
2. Stop the stale host process and restart uvicorn from the **current git SHA** if host mode is still required.

**Verification (compose):**

```bash
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health/ready').status_code)"
# Expect 200 when postgres is healthy
```

**Do not** use `:8010` for D4/CIP acceptance unless the host binary is confirmed at the same revision as compose.

---

## Related

| Doc | Topic |
|-----|--------|
| [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) | `BACKEND_BASE_URL` examples |
| [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md) | §10 — never mix URLs on one instance |
| [`n8n-runtime-start.md`](n8n-runtime-start.md) | Legacy host n8n only |
| [`../deployment/n8n-compose.md`](../deployment/n8n-compose.md) | Portable n8n on `alpstein_internal` |
