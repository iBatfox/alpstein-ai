# T14-OC-3 — Add Business Context node (Telegram ingress)

**Status:** **passed** (n8n scope)  
**Date:** 2026-05-25  
**Depends on:** T14-OC-2 backend deployed  
**Runtime workflow id:** `FHSgBtwDm9PyDAl2` (`alpstein-incoming-message-telegram`)

## Goal

Add **Add Business Context** (Edit Fields / Set) after normalize; POST top-level `operator_business_context` to backend. No OpenAI in n8n.

## Workflow change

```text
Telegram Trigger
  → Normalize Telegram Incoming
  → Add Business Context          ← Set v2, keepOnlySet: false
  → POST Backend                  ← jsonBody includes operator_business_context
       ├─ (success) → Shape Telegram Customer Reply → Telegram Send Message
       ├─ (success) → IF Notify Owner → … → Telegram Owner Notify
       └─ (error)   → Format Telegram Backend Error → Telegram Send Message
```

## Context text (MVP, in Set node)

```text
Barbershop demo business.
Services: haircut, beard trim, appointment requests.
Opening hours: Monday to Friday, 09:00-18:00.
Languages: German, English, Russian.
Tone: friendly, concise, helpful.
If the customer writes in Russian, answer in Russian.
Ask for the customer's name only when they clearly want to book an appointment.
```

## Implementation notes

| Item | Detail |
|------|--------|
| Node type | `n8n-nodes-base.set` v2 (`keepOnlySet: false`) |
| Set v3 `includeOtherFields` | **Rejected** — dropped normalized fields → backend 422 missing `business_id` |
| POST body | `operator_business_context: $json.operator_business_context` plus contract fields |
| Export | `versionId: t14-oc3-business-context-v2`; no secrets |

## Verification (2026-05-25)

### Export / import

| Check | Result |
|-------|--------|
| JSON valid | Pass |
| Secret scan | Pass |
| `operator_business_context` in export | Pass |
| No OpenAI node | Pass |

### n8n executions (`FHSgBtwDm9PyDAl2`, webhook inject)

| Scenario | Exec ID | Chain | `operator_business_context` in POST | Backend | Owner notify |
|----------|---------|-------|--------------------------------------|---------|--------------|
| RU hours question | **68** | Full | Yes | 200 `success` | Skipped |
| RU booking intent | **69** | Full | Yes | 200 `success` | Skipped |
| URGENT (EN) | **70** | Full | Yes | 200 `notify_owner` | **Ran** |
| Duplicate same `msg_id` | **71** | Full | Yes | 200 `is_duplicate` | Skipped |

### Backend direct (sanity)

| Test | Result |
|------|--------|
| Field accepted | Pass |
| Not in response | Pass |
| Duplicate idempotency | Pass (`second_dup=true`, `second_notify=false`) |
| Hours in reply | Pass (`mentions_hours`) |
| Cyrillic reply | **Partial** — AI often replies in English despite operator note; not an n8n wiring issue |

### Russian test expectations

| Requirement | Result |
|-------------|--------|
| Does not say “only German/English” | Pass |
| Reflects hours / business context | Pass |
| Reply in Russian | **Partial** — prompt/AI follow-up outside T14-OC-3 |
| Booking asks name when appropriate | Pass (exec 69) |

## Post-test runtime

- Duplicate telegram workflow imports set **inactive**; only `FHSgBtwDm9PyDAl2` was active for tests.
- Workflow **deactivated** after verification (repo export remains `active: false`).

## T14.5 gate

**T14.5 MAY START** — Telegram regression (owner notify + duplicate) on workflow with OC-3 node.
