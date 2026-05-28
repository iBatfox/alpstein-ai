**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

# Next Steps

## Recommended next task: **Website Chat widget MVP implementation** (after E1.4 identity-strategy review)

Phase **E0** closed: [`e0-telegram-reference-channel-remediation-2026-05-28.md`](../audits/e0-telegram-reference-channel-remediation-2026-05-28.md) — **PASS WITH WARNINGS** · Telegram reference channel baseline established.

**E1.0–E1.2 (spec-only):** ingress contract, Telegram/website mapping, canonical API alignment.  
**E1.3 completed (spec-only):** [`website-chat-architecture.md`](../architecture/website-chat-architecture.md) · [`T-e1.3-website-chat-architecture.md`](../../tasks/done/T-e1.3-website-chat-architecture.md).  
**E1.4 completed (spec-only):** [`multi-channel-identity-strategy.md`](../architecture/multi-channel-identity-strategy.md) · [`T-e1.4-multi-channel-identity-strategy.md`](../../tasks/done/T-e1.4-multi-channel-identity-strategy.md).

Implementation order: widget MVP -> n8n adapter -> compose E2E (see `website-chat-architecture.md` §16). Do **not** change Telegram runtime.

| Step | Status | Notes |
|------|--------|-------|
| **T14.5 / T-e0** | **done (WARN)** | Exec **222**; prompt_run `e426d4bc-…` |
| **E0 optional hardening** | planned | Real DM; `docker-compose up n8n`; Langfuse on compose backend |
| **CIP-D** | **planned** | Live intent metadata smoke |
| **Phase E1.0** | **done (design)** | Normalized ingress contract documented; no runtime changes |
| **Phase E1.1** | **done (design)** | Telegram + Website Chat mapping matrix documented |
| **Phase E1.2** | **done (spec)** | Canonical API/spec field matrix locked; runtime unchanged |

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

## Phase E1 — channel expansion contract

| Slice | Status |
|-------|--------|
| E1.0 channel ingress contract | **done (design-only)** |
| E1.1 Telegram/Website Chat mapping detail | **done (spec-only)** |
| E1.2 API/spec field alignment | **done (spec-only)** |
| E1.3 Website Chat architecture | **done (spec-only)** |
| E1.4 Multi-channel identity strategy | **done (spec-only)** |
| Website Chat widget MVP | **next (after review)** |
| n8n website-chat adapter | planned |
| Website Chat E2E on compose | planned |
| Runtime channel integrations (WhatsApp/Instagram/etc.) | **deferred** |

Reference: [`website-chat-architecture.md`](../architecture/website-chat-architecture.md), [`multi-channel-identity-strategy.md`](../architecture/multi-channel-identity-strategy.md), [`normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md), [`channel-ingress-contract.md`](../architecture/channel-ingress-contract.md), [`channel-mapping-telegram-website.md`](../architecture/channel-mapping-telegram-website.md), [`T-e1.0-channel-ingress-contract.md`](../../tasks/done/T-e1.0-channel-ingress-contract.md), [`T-e1.1-telegram-website-channel-mapping.md`](../../tasks/done/T-e1.1-telegram-website-channel-mapping.md), [`T-e1.2-api-spec-alignment-channel-contract.md`](../../tasks/done/T-e1.2-api-spec-alignment-channel-contract.md), [`T-e1.3-website-chat-architecture.md`](../../tasks/done/T-e1.3-website-chat-architecture.md), [`T-e1.4-multi-channel-identity-strategy.md`](../../tasks/done/T-e1.4-multi-channel-identity-strategy.md).

---

## Conversation Intent Policy

| Slice | Status |
|-------|--------|
| CIP-B PromptBuilder wire | **done** |
| CIP-C D1 / D2 | **done** (contract + runtime wiring) |
| CIP-D Telegram live smoke | **open** |

---

## Repository hygiene (E0)

| Item | Status | Notes |
|------|--------|-------|
| **E0** n8n script layout | **done** (docs) | [`repository-layout-n8n-scripts.md`](../ops/repository-layout-n8n-scripts.md) — **TD-D4-n8n-script-layout** closed; no file moves |

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
