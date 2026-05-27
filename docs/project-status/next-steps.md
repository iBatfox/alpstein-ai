**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

**Doc status:** canonical (open-work queue)  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) · Docs index: [`../README.md`](../README.md)

# Next Steps

## Recommended next task: **P0 git stabilization** (commit C2 scrub + C1 parity docs) then **C5 / T14.5**

**RBU drill (2026-05-27):** [`disposable-rbu-drill-2026-05-27.md`](../audits/disposable-rbu-drill-2026-05-27.md) — **CONDITIONAL NO-GO** Phase D until export-scrub is in git.

### Phase C — n8n runtime/export parity

| Step | Status | Notes |
|------|--------|-------|
| **C1** | **done** | [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md), [`T-c1-n8n-runtime-export-parity.md`](../../tasks/done/T-c1-n8n-runtime-export-parity.md) |
| C2 / T14.6 | **done** | [`export-scrub.sh`](../../scripts/n8n/export-scrub.sh) — [`T14.6-n8n-export-scrub-parity-gate.md`](../../tasks/done/T14.6-n8n-export-scrub-parity-gate.md) |
| **C3** | planned | Runtime vs export diff |
| **C4** | planned | Pre-deploy parity checklist script |
| **C5 / T14.5** | planned | Telegram regression on canonical export |
| **C6** | planned | Clean-clone G5 webhook import path |

**CIP-C Phase D:** D1 observability metadata **approved** (§16 defaults locked). **D2** Langfuse runtime metadata wiring **implemented** (pending review) — [`T-d2-langfuse-runtime-metadata-wiring.md`](../../tasks/done/T-d2-langfuse-runtime-metadata-wiring.md). **Next: D3** n8n correlation headers (when tasked).

### Deployment portability (B2)

| Phase | Status | Notes |
|-------|--------|-------|
| B2.0 | **done** | [`deployment-contract.md`](../deployment/deployment-contract.md) |
| B2.1 | **done** | Env templates tracked; spec/ops drift marked — [`T-b2.1-deployment-governance-artifacts.md`](../../tasks/done/T-b2.1-deployment-governance-artifacts.md) |
| B2.2 | **done** | [`docker-compose.yml`](../../docker-compose.yml) postgres only — [`T-b2.2-postgres-compose-service.md`](../../tasks/done/T-b2.2-postgres-compose-service.md) |
| B2.3 | **done** | [`backend/Dockerfile`](../../backend/Dockerfile) — [`T-b2.3-backend-dockerfile-image-build.md`](../../tasks/done/T-b2.3-backend-dockerfile-image-build.md) |
| B2.4 | **done** | Readiness endpoint |
| B2.5 | **done** | [`docker-entrypoint.sh`](../../backend/docker-entrypoint.sh) — [`T-b2.5-backend-entrypoint-contract.md`](../../tasks/done/T-b2.5-backend-entrypoint-contract.md) |
| B2.6 | **done** | Root compose `backend` — [`T-b2.6-backend-compose-service.md`](../../tasks/done/T-b2.6-backend-compose-service.md) |
| **B2.7** | **done** | n8n on `alpstein_internal` — [`n8n-compose.md`](../deployment/n8n-compose.md), [`T-b2.7-n8n-internal-compose-network.md`](../../tasks/done/T-b2.7-n8n-internal-compose-network.md) |
| B2.8 | **done** | [`bootstrap-profile.md`](../deployment/bootstrap-profile.md) — [`T-b2.8-bootstrap-dev-seed-profile.md`](../../tasks/done/T-b2.8-bootstrap-dev-seed-profile.md) |
| B2.9 | **done** | [`clean-clone-gate-2026-05-27.md`](../audits/clean-clone-gate-2026-05-27.md) — [`T-b2.9-clean-clone-verification-gate.md`](../../tasks/done/T-b2.9-clean-clone-verification-gate.md) |

Compose: [`postgres-compose.md`](../deployment/postgres-compose.md), [`n8n-compose.md`](../deployment/n8n-compose.md). Image + entrypoint: [`backend-image.md`](../deployment/backend-image.md).

**HF-1 (done):** History safety preamble in §7 — [`HF-1-history-safety-promptbuilder.md`](../../tasks/done/HF-1-history-safety-promptbuilder.md). Plan: [`Plan Context Freshness History Safety Policy.md`](../../tasks/done/Plan%20Context%20Freshness%20History%20Safety%20Policy.md).

---

## T14 remaining (Telegram ops)

| ID | Task | Notes |
|----|------|-------|
| **T14.5** | Owner-notify + duplicate regression (Telegram path) | Unblocked after Alpstein AI greeting switch |
| **T14.6** | **done** | G-EXP-2 gate — run `scripts/n8n/export-scrub.sh` before workflow commits |

Plan reference: [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md) (T14.1–T14.4 and T14-OC **done**).

**Alpstein AI greeting switch (done):** exec **89–91** — [`T14-switch-alpstein-ai-greeting-n8n.md`](../../tasks/done/T14-switch-alpstein-ai-greeting-n8n.md).

---

## Conversation Intent Policy

| Slice | Status |
|-------|--------|
| Spec | [`conversation-intent-policy-mvp.md`](../architecture/conversation-intent-policy-mvp.md) |
| CIP-A routing foundation | **implemented** (absorbed into CIP-B; `ConversationIntentService`) |
| CIP-B PromptBuilder wire | **done** — [`CIP-B-conversation-intent-promptbuilder.md`](../../tasks/done/CIP-B-conversation-intent-promptbuilder.md) |
| CIP-C D1 observability contract | **approved** (defaults §16) |
| CIP-C D2 Langfuse + context propagation | **implemented** (pending review) |
| CIP-D Telegram live smoke | **open** (after CIP-C D2) |

Contact ownership backend cleanup **done** — [`CIP-contact-ownership-backend-cleanup.md`](../../tasks/done/CIP-contact-ownership-backend-cleanup.md). **Ops:** add contact block to n8n `operator_business_context` ([`pre-sales-contact-ownership.md`](../architecture/pre-sales-contact-ownership.md)).

---

## Completed gates

| Gate | Status |
|------|--------|
| T13.5 / Gate 2 (owner notify) | Passed |
| T14.1–T14.4 (Telegram pipeline) | Passed |
| T14-OC-1–3 (operator business context) | Done |
| Alpstein AI greeting switch | Passed — exec 89–91 |
| CIP-B intent in PromptBuilder | Done (Alpstein demo business) |

---

## Operator business context

| ID | Status |
|----|--------|
| T14-OC-1 | Spec done |
| T14-OC-2 | Backend done |
| T14-OC-3 | n8n Set node done |

Design: [`operator-business-context-n8n.md`](../architecture/operator-business-context-n8n.md)

**Deferred:** T13.6 retries/errors, T13.7 full E2E, ATTR-3 attribution persistence.

---

## Reference

| Doc | Topic |
|-----|--------|
| [`current-state.md`](current-state.md) | Regeneratable runtime snapshot |
| [`completed.md`](completed.md) | Shipped changelog |
| [`engineering-archive.md`](engineering-archive.md) | Engineering history |
| [`engineering-audit-report.md`](engineering-audit-report.md) | Drift audit (2026-05) |
| [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md) | Dual-bot model |
| [`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md) | Telegram ingress ops |
| [`langfuse-tracing.md`](../architecture/langfuse-tracing.md) | Dev tracing |
| [`deployment-contract.md`](../deployment/deployment-contract.md) | Portable deploy contract |
| [`deployment/README.md`](../deployment/README.md) | Deployment doc index |
