**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

# Next Steps

## Recommended next task: **Phase E — controlled expansion prep (T14.5 / C5 on compose)**

Phase **D4** operational verification is **complete**. Verdict: **stable with known operational limits** — see [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

**Do not** start new channel work (e.g. WhatsApp) until **T14.5** Telegram regression passes on the **portable compose** path with canonical workflow export + G-EXP-2 scrub.

| Step | Status | Notes |
|------|--------|-------|
| **T14.5 / C5** | **planned** | Owner-notify + duplicate matrix on Telegram; `BACKEND_BASE_URL=http://backend:8000` |
| **CIP-D** | **planned** | Live smoke on `alpstein_ai_demo_001` for intent metadata in DB |
| **D4.3-R2** (optional) | **planned** | Disposable failure drill for `prompt_runs.error` |
| **C3 / C4** | **planned** | Runtime vs export diff; pre-deploy parity script |
| **Phase E channel expansion** | **blocked** | Until T14.5 + ingress policy confirmed |

**Ingress policy (P0):** [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) — compose SoT; no stale `:8010` for validation.

---

### Phase D4 — operational verification (closed)

| Slice | Status | Evidence |
|-------|--------|----------|
| D4.1 Live trace validation | **done** | [`d4-1-live-trace-validation-2026-05-27.md`](../audits/d4-1-live-trace-validation-2026-05-27.md) |
| D4.2 Compose E2E hardening | **done** | [`d4-2-compose-e2e-hardening-2026-05-28.md`](../audits/d4-2-compose-e2e-hardening-2026-05-28.md) |
| U1 metadata JSON-safe | **done** | `json_safe_metadata()` in `prompt_run_service.py` |
| D4.3 DB replay verification | **done** | [`d4-3-db-replay-verification-2026-05-27.md`](../audits/d4-3-db-replay-verification-2026-05-27.md) |
| D4.4 Production safety audit | **done** | [`d4-4-production-safety-audit-2026-05-27.md`](../audits/d4-4-production-safety-audit-2026-05-27.md) |
| OPS-C1 stale ingress mitigation | **done** | [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) |
| D4.5 Wrap-up | **done** (docs) | [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md) |

---

### Phase C — n8n runtime/export parity

| Step | Status | Notes |
|------|--------|-------|
| **C1** | **done** | [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md) |
| C2 / T14.6 | **done** | [`export-scrub.sh`](../../scripts/n8n/export-scrub.sh) |
| **C3** | planned | Runtime vs export diff |
| **C4** | planned | Pre-deploy parity checklist script |
| **C5 / T14.5** | planned | Telegram regression on canonical export |
| **C6** | planned | Clean-clone G5 webhook import path |

**CIP-C:** D1 observability contract **approved**; D2 Langfuse + context propagation **implemented** — [`T-d2-langfuse-runtime-metadata-wiring.md`](../../tasks/done/T-d2-langfuse-runtime-metadata-wiring.md). **D3** n8n correlation headers — deferred.

---

### Deployment portability (B2) — complete

| Phase | Status | Notes |
|-------|--------|-------|
| B2.0–B2.9 | **done** | Contract through clean-clone gate — [`deployment/README.md`](../deployment/README.md) |

Compose: [`postgres-compose.md`](../deployment/postgres-compose.md), [`n8n-compose.md`](../deployment/n8n-compose.md). Image + entrypoint: [`backend-image.md`](../deployment/backend-image.md).

---

## T14 remaining (Telegram ops)

| ID | Task | Notes |
|----|------|-------|
| **T14.5** | Owner-notify + duplicate regression (Telegram path) | **Next engineering slice** for Phase E readiness |
| **T14.6** | **done** | G-EXP-2 gate |

Plan reference: [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md) (T14.1–T14.4 and T14-OC **done**).

---

## Conversation Intent Policy

| Slice | Status |
|-------|--------|
| CIP-B PromptBuilder wire | **done** |
| CIP-C D1 / D2 | **done** (contract + runtime wiring) |
| CIP-D Telegram live smoke | **open** |

---

## Deferred (does not block Phase E planning)

T13.6 retries/errors, T13.7 full E2E, ATTR-3 attribution persistence, WhatsApp ingress, Kubernetes, CRM expansion, legacy host decommission.

---

## Reference

| Doc | Topic |
|-----|--------|
| [`current-state.md`](current-state.md) | Regeneratable runtime snapshot |
| [`completed.md`](completed.md) | Shipped changelog |
| [`engineering-archive.md`](engineering-archive.md) | Engineering history |
| [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md) | D4 verdict + Phase E boundaries |
| [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) | Single ingress SoT |
| [`deployment-contract.md`](../deployment/deployment-contract.md) | Portable deploy contract |
