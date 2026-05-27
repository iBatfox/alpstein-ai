**Doc status:** runtime-derived  
**Tier:** conversational/policies (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) §4 — **implemented**

# Operator business context via n8n (MVP design)

**Status:** T14-OC-1 spec done; **T14-OC-2 backend done**; **T14-OC-3 n8n Set node done** (2026-05-25)  
**Date:** 2026-05-25  
**Canonical contract:** [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7, [`prompt-builder-rules.md`](../../specs/architecture/prompt-builder-rules.md) §4.5  
**Decision:** n8n may hold an editable **business context** block; **OpenAI, Prompt Builder, PromptRun, and fallback remain in backend only.**

**Related:** [`ai-configuration-architecture.md`](../../specs/architecture/ai-configuration-architecture.md), [`prompt-builder-rules.md`](../../specs/architecture/prompt-builder-rules.md), [`telegram-customer-ingress.md`](../ops/telegram-customer-ingress.md)

---

## Goal

Operators edit simple business facts/instructions in n8n (per business workflow) without duplicating prompt assembly or calling OpenAI from n8n.

**MVP success:** Telegram (and test) path sends optional context metadata → backend merges it into Prompt Builder **reference data** → AI reply reflects context; platform safety layers unchanged.

---

## Proposed n8n topology (approved pattern)

```text
Telegram Trigger
  → Normalize Telegram Incoming
  → Add Business Context          ← Set node (T14-OC-3): static multiline operator_business_context
  → POST Backend
  → Shape Telegram Customer Reply
  → Telegram Send Message
  → (existing) IF notify_owner → owner Telegram (Alpstein credential)
```

**Forbidden in n8n:** OpenAI node, HTTP to OpenAI, prompt template assembly, lead/notify business rules.

---

## Backend contract (T14-OC-2 — live)

| Property | Rule |
|----------|------|
| Field | Top-level `operator_business_context` on `POST /api/v1/webhook/message` |
| Type | `string` or `null` (optional) |
| Max length | **8192** characters |
| Normalization | Empty or whitespace-only → `null` |
| Persistence | **Not** stored in PostgreSQL MVP (no message column) |
| Response | **Never** returned in webhook JSON |
| AI path | `WebhookMessageService` → `AiReplyOrchestrationCoordinator` → `PromptBuilderService` |
| Prompt placement | Section `tenant_business_context`, **after** DB `TenantBusinessProfile` text, sub-block `OPERATOR BUSINESS NOTES` |
| Lead signals | **Only** `message.text` — operator field ignored |

Single backend task **T14-OC-2** covers: Pydantic schema, service wire, Prompt Builder append, tests.

---

## Answers to planning questions

### 1. Can current backend webhook schema accept extra metadata without code changes?

**Before T14-OC-2:** extra top-level fields were ignored. **Now:** `operator_business_context` is the supported contract field.

`message.raw_payload` remains audit/debug only — **not** Prompt Builder input.

### 2. Where should n8n place it?

**Canonical:** top-level optional string:

```json
{
  "business_id": "alpstein_ai_demo_001",
  "channel": "telegram",
  "operator_business_context": "Alpstein AI demo business. We help businesses with AI assistants, CRM integrations, workflow automation, Telegram AI assistants, and customer communication systems. Reply in the customer's language. Tone: calm, clear, concise.",
  "customer": { ... },
  "message": { ... }
}
```

**Do not place:** inside `message.text`, fake `customer.*`, or `raw_payload` as primary AI context.

### 3. Minimal backend change (completed)

| Step | Task | Status |
|------|------|--------|
| **OC-1** | Spec in `webhooks.md`, `api-endpoints.md`, `prompt-builder-rules.md` §4.5 | **done** |
| **OC-2** | Schema + service wire + Prompt Builder + tests | **done** |
| **OC-3** | n8n Add Business Context Set node | **done** — [`T14-OC-3-add-business-context-node.md`](../../tasks/done/T14-OC-3-add-business-context-node.md) |

### 4. Avoid duplicating prompt logic in n8n

| n8n MAY send | n8n MUST NOT send |
|--------------|-------------------|
| Business facts, hours, tone reminders | System prompts, safety overrides, API keys |
| Short FAQ bullets | OpenAI parameters, tool definitions |

**Merge rule:** DB profile **first**; operator string **appended** under `OPERATOR BUSINESS NOTES`. Platform sections **1–2** always win.

### 5. MVP context format

Single multiline string, max **8192** characters (not 8000). Plain-language facts only.

---

## Tenant / business scoping

Context applies only to the resolved `business_id` on that request. One n8n workflow per client bot.

---

## Spec alignment (resolved)

| Former gap | Resolution |
|------------|------------|
| Field missing from `webhooks.md` | OC-1 §7 |
| No Prompt Builder subsection | OC-1 `prompt-builder-rules.md` §4.5; OC-2 implementation |
| DB vs operator precedence | DB profile first; operator additive |
| `raw_payload` as AI path | Explicitly forbidden; use `operator_business_context` |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Prompt injection via operator block | Platform sections first; reference-only label |
| Drift vs `tenant_business_profiles` | Document precedence; DB canonical |
| Secrets in context field | Ops training; max length; do not log in responses |

---

## Sequencing

| Order | Item |
|-------|------|
| Done | T14-OC-1 spec, **T14-OC-2 backend** |
| **Next** | **T14.5** — Telegram regression with OC-3 workflow |

**Runtime workflow (OC-3):** `FHSgBtwDm9PyDAl2` — import from [`t14_workflow_telegram_customer_ingress_skeleton.json`](../../n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json).
