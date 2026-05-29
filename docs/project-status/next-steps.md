**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

# Next Steps

## Recommended next task: **E3.5d Postgres concurrency validation** → E3.6 staging validation → enable flags

**E3.6 (implemented, review):** Anti-spam protection — [`e3-6-anti-spam-protection.md`](../audits/e3-6-anti-spam-protection.md) · tasks `T-e3.6*` in `tasks/done/` — **keep `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false` until E3.5d + staging green**

**E3.5d (todo, parallel):** Postgres rate-limit concurrency — [`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md) · keep `ALPSTEIN_AI_RATE_LIMIT_ENABLED=false` until green

**E3.5 (accepted):** Rate limiting — [`e3-5-rate-limiting.md`](../audits/e3-5-rate-limiting.md) · deploy migrations `0018` with flag **off**

**E3.4 (done):** Ingress failure isolation — [`e3-4-ingress-failure-isolation.md`](../audits/e3-4-ingress-failure-isolation.md) · tasks `T-e3.4a`–`T-e3.4c` in `tasks/done/`

**E3.3 (done):** Adapter monitoring — [`e3-3-adapter-monitoring.md`](../audits/e3-3-adapter-monitoring.md) · tasks `T-e3.3a`–`T-e3.3c` in `tasks/done/`

**E3.2 (done):** Retry/dead-letter — [`e3-2-retry-dead-letter.md`](../audits/e3-2-retry-dead-letter.md) · tasks `T-e3.2a`–`T-e3.2c` in `tasks/done/`

**E3.1 (done):** Retry/replay protection — [`T-e3.1a-in-flight-replay-protection.md`](../../tasks/done/T-e3.1a-in-flight-replay-protection.md), [`T-e3.1b-terminal-delivery-state-machine.md`](../../tasks/done/T-e3.1b-terminal-delivery-state-machine.md), [`T-e3.1c-replay-observability.md`](../../tasks/done/T-e3.1c-replay-observability.md); audit [`e3-1-retry-replay-protection.md`](../audits/e3-1-retry-replay-protection.md). Deploy: `alembic upgrade head` (0013–0014) + backend restart.

**E2.7 (done):** E2 observability verification — [`T-e2.7-end-to-end-observability-verification.md`](../../tasks/done/T-e2.7-end-to-end-observability-verification.md), audit [`e2-observability-verification.md`](../audits/e2-observability-verification.md).

**E2.6 (done):** delivery visibility — [`T-e2.6-delivery-visibility.md`](../../tasks/done/T-e2.6-delivery-visibility.md).

**E2.5 (done):** observability APIs — [`T-e2.5-observability-api-extensions.md`](../../tasks/done/T-e2.5-observability-api-extensions.md).

**E2.4 (done):** `message_traces` persistence — Alembic `0011`, [`T-e2.4-message-trace-persistence.md`](../../tasks/done/T-e2.4-message-trace-persistence.md).

**E2.3 (done):** inbound message uniqueness — Alembic `0010`, [`T-e2.3-message-uniqueness-hardening.md`](../../tasks/done/T-e2.3-message-uniqueness-hardening.md).

**E2.2 (done):** `conversations.flow_id` + flow-scoped lookup — Alembic `0009`, [`T-e2.2-conversation-flow-scoping.md`](../../tasks/done/T-e2.2-conversation-flow-scoping.md).

**E2.0 (done, design-only):** Unified conversation + observability — [`unified-conversation-observability.md`](../architecture/unified-conversation-observability.md) · [`T-e2.0-unified-conversation-observability-design.md`](../../tasks/done/T-e2.0-unified-conversation-observability-design.md) · verdict **PASS WITH NOTES**.

**OPS-H1** closed: [`runtime-surface-hardening.md`](../ops/runtime-surface-hardening.md) — canonical map in [`runtime-map.md`](../ops/runtime-map.md).

**RECOVERY-2** closed: [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md) — use **`docker compose`** (v2) for stack ops; never `docker-compose --force-recreate` on v1.

Phase **E0** closed: [`e0-telegram-reference-channel-remediation-2026-05-28.md`](../audits/e0-telegram-reference-channel-remediation-2026-05-28.md) — **PASS WITH WARNINGS** · Telegram reference channel baseline established.

**E1.0–E1.2 (spec-only):** ingress contract, Telegram/website mapping, canonical API alignment.  
**E1.3 completed (spec-only):** [`website-chat-architecture.md`](../architecture/website-chat-architecture.md) · [`T-e1.3-website-chat-architecture.md`](../../tasks/done/T-e1.3-website-chat-architecture.md).  
**E1.4 completed (spec-only):** [`multi-channel-identity-strategy.md`](../architecture/multi-channel-identity-strategy.md) · [`T-e1.4-multi-channel-identity-strategy.md`](../../tasks/done/T-e1.4-multi-channel-identity-strategy.md).
**E1.5 completed (spec-only):** [`channel-capability-matrix.md`](../architecture/channel-capability-matrix.md) · [`T-e1.5-channel-capability-matrix.md`](../../tasks/done/T-e1.5-channel-capability-matrix.md).  
**E1.6 implemented (runtime slice):** [`n8n-workflow-website-chat-mvp.md`](../ops/n8n-workflow-website-chat-mvp.md) · [`T-e1.6-website-chat-mvp-runtime.md`](../../tasks/done/T-e1.6-website-chat-mvp-runtime.md).

Implementation follow-up: E1.6.3 runtime compatibility fix and E1.6.6 activation semantics verification are complete for Website Chat.

| Step | Status | Notes |
|------|--------|-------|
| **OPS-H1** | **done (WARN)** | Runtime map; `0.0.0.0` dev servers flagged |
| **RECOVERY-2** | **done (WARN)** | `docker compose` v2; recreate path safe |
| **RECOVERY-1** | **done (WARN)** | Postgres/backend/n8n SoT; webhook smokes 200 |
| **T14.5 / T-e0** | **done (WARN)** | Exec **222**; prompt_run `e426d4bc-…` |
| **E0 optional hardening** | planned | Real DM; `docker-compose up n8n`; Langfuse on compose backend; fix compose recreate |
| **CIP-D** | **planned** | Live intent metadata smoke |
| **Phase E1.0** | **done (design)** | Normalized ingress contract documented; no runtime changes |
| **Phase E1.1** | **done (design)** | Telegram + Website Chat mapping matrix documented |
| **Phase E1.2** | **done (spec)** | Canonical API/spec field matrix locked; runtime unchanged |
| **Phase E1.6.2** | **done** | Live smoke + runtime evidence documented |
| **Phase E1.6.3** | **done** | Runtime compatibility fix + re-smoke + evidence |
| **Phase E1.6.6** | **done** | Explicit kill switch semantics (`ALPSTEIN_WEBSITE_CHAT_ENABLED`) verified on production URL |
| **Phase E1.7** | **done** | Unified customer ingress workflow design — [`unified-customer-ingress-workflow.md`](../architecture/unified-customer-ingress-workflow.md) |
| **Phase E1.8** | **done** | Unified ingress workflow JSON + inactive import — [`e1-8-unified-ingress-inactive-implementation-2026-05-28.md`](../audits/e1-8-unified-ingress-inactive-implementation-2026-05-28.md) |
| **Phase E1.9** | **done** | Production cutover to `alpstein-customer-ingress` — [`e1-9-unified-ingress-cutover-2026-05-28.md`](../audits/e1-9-unified-ingress-cutover-2026-05-28.md) |
| **Phase E2.0** | **done (design)** | Conversation + observability model — no runtime |

**Ingress policy (P0):** [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) — compose SoT; no stale `:8010` for validation.

---

## Phase E2 — conversation continuity + observability

| Slice | Status | Notes |
|-------|--------|-------|
| **E2.0** | **done (design)** | [`unified-conversation-observability.md`](../architecture/unified-conversation-observability.md), [`message-debugging-runbook.md`](../ops/message-debugging-runbook.md) |
| E2.1 | **done** | [`e2-1-flows-migration-default-flows-2026-05-28.md`](../audits/e2-1-flows-migration-default-flows-2026-05-28.md) — `flows` table + default flows + webhook resolution |
| E2.2 | **done** | [`T-e2.2-conversation-flow-scoping.md`](../../tasks/done/T-e2.2-conversation-flow-scoping.md) — `conversations.flow_id` + flow-scoped lookup (Alembic `0009`) |
| E2.3 | **done** | [`T-e2.3-message-uniqueness-hardening.md`](../../tasks/done/T-e2.3-message-uniqueness-hardening.md) — conversation-scoped inbound dedup (Alembic `0010`) |
| E2.4 | **done** | [`T-e2.4-message-trace-persistence.md`](../../tasks/done/T-e2.4-message-trace-persistence.md) — `message_traces` + webhook lifecycle (Alembic `0011`) |
| E2.5 | **done** | [`T-e2.5-observability-api-extensions.md`](../../tasks/done/T-e2.5-observability-api-extensions.md) — read APIs + webhook `data.trace` |
| E2.6 | **done** | [`T-e2.6-delivery-visibility.md`](../../tasks/done/T-e2.6-delivery-visibility.md) — `delivery_events` + observability delivery APIs (Alembic `0012`) |
| E2.7 | **done** | [`T-e2.7-end-to-end-observability-verification.md`](../../tasks/done/T-e2.7-end-to-end-observability-verification.md) — continuity tests + verification harness |
| E2.8 | **next** | Ops gate + Langfuse on compose verification |
| E2 n8n delivery PATCH wiring | **done (repo)** — [`delivery-outcome-patching.md`](../n8n/delivery-outcome-patching.md); runtime import + env UUIDs pending operator |

Golden rule: **one flow = one bot behavior** — see [`unified-conversation-model.md`](../../specs/architecture/unified-conversation-model.md) § Database Separation & Flow Governance.

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
| E1.5 Channel capability matrix | **done (spec-only)** |
| E1.6 Website Chat MVP runtime slice | **implemented** |
| E1.6 smoke verification and hardening | **E1.6.3 blocker fixed + E1.6.6 kill switch semantics verified** |
| **E1.7** unified customer ingress design | **done (spec-only)** — [`unified-customer-ingress-workflow.md`](../architecture/unified-customer-ingress-workflow.md) |
| E1.9 post-cutover | **operator** — live Telegram DM smoke; deploy widget URL to unified path on production sites |
| Runtime channel integrations (WhatsApp/Instagram/etc.) | **deferred** |

Reference: [`website-chat-architecture.md`](../architecture/website-chat-architecture.md), [`multi-channel-identity-strategy.md`](../architecture/multi-channel-identity-strategy.md), [`channel-capability-matrix.md`](../architecture/channel-capability-matrix.md), [`n8n-workflow-website-chat-mvp.md`](../ops/n8n-workflow-website-chat-mvp.md), [`normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md), [`channel-ingress-contract.md`](../architecture/channel-ingress-contract.md), [`channel-mapping-telegram-website.md`](../architecture/channel-mapping-telegram-website.md), [`T-e1.0-channel-ingress-contract.md`](../../tasks/done/T-e1.0-channel-ingress-contract.md), [`T-e1.1-telegram-website-channel-mapping.md`](../../tasks/done/T-e1.1-telegram-website-channel-mapping.md), [`T-e1.2-api-spec-alignment-channel-contract.md`](../../tasks/done/T-e1.2-api-spec-alignment-channel-contract.md), [`T-e1.3-website-chat-architecture.md`](../../tasks/done/T-e1.3-website-chat-architecture.md), [`T-e1.4-multi-channel-identity-strategy.md`](../../tasks/done/T-e1.4-multi-channel-identity-strategy.md), [`T-e1.5-channel-capability-matrix.md`](../../tasks/done/T-e1.5-channel-capability-matrix.md), [`T-e1.6-website-chat-mvp-runtime.md`](../../tasks/done/T-e1.6-website-chat-mvp-runtime.md).

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
