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

## Recommended next task: **B2.6** (compose backend) or **CIP-C** / **T14.5**

### Deployment portability (B2)

| Phase | Status | Notes |
|-------|--------|-------|
| B2.0 | **done** | [`deployment-contract.md`](../deployment/deployment-contract.md) |
| B2.1 | **done** | Env templates tracked; spec/ops drift marked — [`T-b2.1-deployment-governance-artifacts.md`](../../tasks/done/T-b2.1-deployment-governance-artifacts.md) |
| B2.2 | **done** | [`docker-compose.yml`](../../docker-compose.yml) postgres only — [`T-b2.2-postgres-compose-service.md`](../../tasks/done/T-b2.2-postgres-compose-service.md) |
| B2.3 | **done** | [`backend/Dockerfile`](../../backend/Dockerfile) — [`T-b2.3-backend-dockerfile-image-build.md`](../../tasks/done/T-b2.3-backend-dockerfile-image-build.md) |
| B2.4 | **done** | Readiness endpoint |
| B2.5 | **done** | [`docker-entrypoint.sh`](../../backend/docker-entrypoint.sh) — [`T-b2.5-backend-entrypoint-contract.md`](../../tasks/done/T-b2.5-backend-entrypoint-contract.md) |
| **B2.6** | **next** | `backend` service in root `docker-compose.yml` |

Compose: [`postgres-compose.md`](../deployment/postgres-compose.md). Image + entrypoint: [`backend-image.md`](../deployment/backend-image.md).

**HF-1 (done):** History safety preamble in §7 — [`HF-1-history-safety-promptbuilder.md`](../../tasks/done/HF-1-history-safety-promptbuilder.md). Plan: [`Plan Context Freshness History Safety Policy.md`](../../tasks/done/Plan%20Context%20Freshness%20History%20Safety%20Policy.md).

**CIP-C:** Wire Langfuse metadata `conversation_intent`, `intent_matched_rule`, `intent_used_previous_message` at runtime (`langfuse_intent_trace.py` constants exist).

---

## T14 remaining (Telegram ops)

| ID | Task | Notes |
|----|------|-------|
| **T14.5** | Owner-notify + duplicate regression (Telegram path) | Unblocked after Alpstein AI greeting switch |
| **T14.6** | Scrubbed n8n export + repo as source of truth | Formal export hygiene gate |

Plan reference: [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md) (T14.1–T14.4 and T14-OC **done**).

**Alpstein AI greeting switch (done):** exec **89–91** — [`T14-switch-alpstein-ai-greeting-n8n.md`](../../tasks/done/T14-switch-alpstein-ai-greeting-n8n.md).

---

## Conversation Intent Policy

| Slice | Status |
|-------|--------|
| Spec | [`conversation-intent-policy-mvp.md`](../architecture/conversation-intent-policy-mvp.md) |
| CIP-A routing foundation | **implemented** (absorbed into CIP-B; `ConversationIntentService`) |
| CIP-B PromptBuilder wire | **done** — [`CIP-B-conversation-intent-promptbuilder.md`](../../tasks/done/CIP-B-conversation-intent-promptbuilder.md) |
| CIP-C Langfuse metadata | **open** |
| CIP-D Telegram live smoke | **open** (after CIP-C) |

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
