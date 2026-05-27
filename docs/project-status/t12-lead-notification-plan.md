**Doc status:** archived  
**Tier:** project-status/historical (pending move)  
**Note:** T12 slice complete — runtime in [`canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

# T12 — Lead creation & owner notification (design plan)

**Status:** design only — stop for review before implementation  
**Date:** 2026-05-24  
**Depends on:** T10 webhook orchestration, T11 AI reply path (complete)

**Goal:** Define MVP rules for lead creation and `notify_owner` so implementation stays spec-aligned, idempotent, and channel-independent.

**MVP success (when implemented):** First non-duplicate customer contact creates a lead in PostgreSQL; follow-up messages update the active lead without duplicates; webhook response exposes accurate `lead_created` / `lead_updated` / `notify_owner` (+ optional `notification` payload); duplicate webhooks never create duplicate leads or owner alerts; n8n can branch on flags without business logic.

**Task breakdown:** [`tasks/todo/t12-lead-notification-slice.md`](../../tasks/todo/t12-lead-notification-slice.md)

---

## Spec alignment

| Item | Verdict |
|------|---------|
| In MVP | **Yes** — `specs/mvp/mvp-scope.md` §4.7 Leads, §4.9 Notifications |
| Primary specs | `specs/flows/lead-creation-flow.md`, `specs/flows/notification-flow.md`, `specs/flows/incoming-message-flow.md` (Steps 20–24), `specs/api/webhooks.md`, `specs/api/api-endpoints.md`, `specs/database/database-schema.md` §9 |
| Out of scope (T12) | n8n workflow implementation, CRM/spreadsheet routing, `lead_routing_rules` table, notification delivery logs, business-hours batching, AI-only lead qualification, vector/memory |

---

## 1. Event ownership

### Backend owns

| Responsibility | Where |
|----------------|--------|
| Lead create / update / dedup decisions | `LeadService` (+ `WebhookMessageService` orchestration) |
| Persist leads in PostgreSQL | `LeadService` via `AsyncSession` (T4–T11 pattern — no generic repository layer) |
| Compute `lead_created`, `lead_updated`, `notify_owner` | Backend notification policy (pure function or small service) |
| Build optional `notification` DTO for n8n | Backend response layer |
| Tenant / business / customer / conversation scoping on all lead queries | Mandatory `tenant_id` + `business_id` filters |
| Idempotency: duplicate inbound message → no lead side effects | Reuse `is_duplicate` from T5–T11 |
| Urgent / human-request detection for **flags only** (MVP heuristics) | Backend keyword rules — not n8n |

### n8n owns (after T12 backend contract is stable)

| Responsibility | Where |
|----------------|--------|
| Deliver owner notifications (Telegram MVP) | n8n notification workflow |
| Format notification copy from backend `notification` object | n8n templates |
| Send customer reply via provider API | n8n reply workflow |
| Retry failed notification delivery | n8n execution / retry policy |
| Future: CRM, spreadsheet, external webhook routing | n8n integrations |

### n8n must NOT own

- Lead creation, update, or dedup logic  
- Lead qualification or status transitions  
- Deciding `notify_owner` (only **branch** on the flag)  
- Prompt / AI orchestration  
- PostgreSQL writes  
- Interpreting duplicate webhooks beyond backend flags  

---

## 2. Lead creation trigger rules (MVP)

### Spec resolution

`lead-creation-flow.md` §21 (MVP simplification) **wins** over `incoming-message-flow.md` Step 20 intent detection:

> Create lead on **first incoming customer message** even if business intent is not fully clear.

Step 20 “detect intent” is satisfied in MVP by **first contact = lead**, not by a separate AI classifier.

### When to **create** a new lead

All must be true:

1. Inbound payload is a **customer** message (already true for `POST /webhook/message`).  
2. `is_duplicate == false`.  
3. No **active lead** exists for:

```text
tenant_id + business_id + customer_id + conversation_id
status IN ('new', 'in_progress', 'contacted')
```

**Initial fields:** `status = new`, `priority = normal`, `source_channel = channel`, `customer_note` = truncated inbound text (optional), `service_requested` / dates null unless enriched later.

**Result flags:** `lead_created = true`, `lead_updated = false`.

### When to **update / reuse** existing active lead

1. `is_duplicate == false`.  
2. Active lead exists (same lookup as above).  

**Update behavior (MVP minimal):**

- Touch `updated_at`.  
- Append or refresh `customer_note` with latest inbound snippet (cap length).  
- Set `status = in_progress` if currently `new` and this is a follow-up message.  
- Bump `priority` to `urgent` if urgent heuristic matches (§3).  

**Result flags:** `lead_created = false`, `lead_updated = true`.

### When **not** to create or update

| Condition | Lead action | Rationale |
|-----------|-------------|-----------|
| `is_duplicate == true` | **Skip** lead create/update | `lead-creation-flow.md` §6.1, §5 |
| Message from AI / owner / system | N/A (not this endpoint) | §5 |
| Active lead exists | **Update**, not create | §6.4 dedup |
| Prior lead `closed` or `lost` | **Create new lead** | New active opportunity cycle |

### Business intent in MVP

| MVP rule | Detail |
|----------|--------|
| Default | First non-duplicate customer message ⇒ lead |
| Intent keywords | **Not required** to create a lead |
| Enrichment (optional) | AI may fill `service_requested`, `ai_summary` later — backend still owns create/update |
| Urgent intent | Simple **keyword heuristic** on inbound text (§3) — not AI-dependent |

**MVP urgent keywords (illustrative):** `urgent`, `emergency`, `call me now`, `asap`, `immediately`, `today` (case-insensitive substring match).

**MVP human-handoff keywords (illustrative):** `speak to a human`, `real person`, `call me`, `manager`, `not a bot`.

---

## 3. `notify_owner` semantics

### Decision table (MVP)

| Scenario | `lead_created` | `lead_updated` | `notify_owner` | `notification.type` |
|----------|----------------|----------------|----------------|---------------------|
| Duplicate webhook (`is_duplicate=true`) | `false` | `false` | **`false`** | — |
| New lead created | `true` | `false` | **`true`** | `new_lead` |
| Active lead updated (routine follow-up) | `false` | `true` | **`false`** | — |
| New or updated lead + `priority=urgent` | either | either | **`true`** | `urgent_lead` |
| AI failure → customer received **fallback** reply | per §2 | per §2 | **`true`** | `ai_failure` |
| Human-handoff keyword heuristic matched | per §2 | per §2 | **`true`** | `human_handoff` |
| Successful AI reply, routine lead update only | `false` | `true` | **`false`** | — |

**Priority rule:** `notify_owner = true` if **any** notify condition matches. When multiple match, use highest `notification.priority` (`urgent` > `high` > `normal`).

### Relation to `lead_created`

- **`lead_created=true` ⇒ `notify_owner=true`** (new contact alert).  
- **`lead_created=false` does not imply `notify_owner=false`** — urgent, AI failure, or human-handoff can still notify.  
- **`lead_updated=true` alone ⇒ `notify_owner=false`** unless urgent / handoff / AI failure also applies.

### Relation to AI fallback / handoff

| AI outcome | Lead still created/updated? | Notify owner? |
|------------|----------------------------|---------------|
| AI success (normal reply) | Yes (per §2) | Only if new lead, urgent, or handoff keyword |
| AI failure → fallback text sent | **Yes** | **`true`** (`ai_failure`) |
| Duplicate → skip AI re-exec (T11.13) | **No** lead change | **`false`** |
| `is_ai_active=false` | Per §2 if not duplicate | **Defer** explicit rule to T12.6; safe default: skip AI, still capture lead, notify on new lead |

**Lead creation does not depend on successful AI reply.**

---

## 4. Idempotency

### Duplicate message (`external_message_id`)

Handled by T5/T6 + T11.13. T12 adds:

```text
if is_duplicate:
  do not create lead
  do not update lead
  notify_owner = false
  return prior reply_to_customer (T11)
```

### Duplicate lead

Prevented by **active lead lookup** before insert (§2). One active lead per `(tenant, business, customer, conversation)` for statuses `new | in_progress | contacted`.

### Duplicate owner notification

Backend sets `notify_owner=false` on duplicate webhooks. n8n must not send owner notification when `notify_owner=false`. Backend contract is the primary guard; n8n-side dedup is a future hardening task.

### Concurrent duplicate insert (T10-F3)

When implemented: treat `IntegrityError` on message insert like duplicate → same lead/notify rules as `is_duplicate=true`.

---

## 5. Duplicate webhook behavior

### Backend returns

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "<last AI reply or safe ack>",
    "lead_created": false,
    "lead_updated": false,
    "notify_owner": false,
    "conversation": { "id": "...", "status": "open" },
    "message": { "id": "...", "is_duplicate": true }
  }
}
```

No `lead` or `notification` objects on duplicate path.

### n8n should

1. Send `reply_to_customer` to the customer (provider API).  
2. **Skip** owner notification branch (`notify_owner=false`).  
3. **Not** infer lead creation from message text or conversation state.  
4. Log `is_duplicate` for tracing only.

---

## 6. AI / fallback dependency

| Question | MVP answer |
|----------|------------|
| Does lead creation require successful AI? | **No** |
| Processing order in `WebhookMessageService` | Inbound save → **lead create/update (if not duplicate)** → AI reply path → **compute notify flags** (needs AI outcome for `ai_failure`) → return |
| Fallback notify owner? | **Yes** when fallback text is sent to customer |
| Does failed AI block lead? | **No** |

---

## 7. T12 task breakdown (summary)

Full table with review gates: [`tasks/todo/t12-lead-notification-slice.md`](../../tasks/todo/t12-lead-notification-slice.md)

| ID | Task | Skill | Depends |
|----|------|-------|---------|
| T12.1 | `leads` migration + `Lead` model | migration-engineer | T11 |
| T12.2 | `LeadService` active-lead lookup + create/update | backend-engineer | T12.1 |
| T12.3 | Notification policy (flags + DTO builder) | backend-engineer | — |
| T12.4 | Urgent / human keyword heuristics | backend-engineer | T12.3 |
| T12.5 | Extend webhook response schemas (`lead_updated`, `lead`, `notification`) | api-designer / backend-engineer | T12.3 |
| T12.6 | Wire lead + notify into `WebhookMessageService` | backend-engineer | T12.2–T12.5, T11 |
| T12.7 | Lead + webhook integration tests | backend-engineer | T12.6 |
| T12.8 | Update project-status docs | backend-engineer | T12.7 |

**Review gates:** after T12.2 (LeadService), after T12.6 (webhook wire-up), after T12.7 (final **alpstein-reviewer**).

**Not in T12:** n8n workflows (future **T13** or n8n slice), CRM routing, `lead_routing_rules`.

---

## 8. n8n handoff

### When we switch to n8n

After backend returns **HTTP 200** with the complete `data` object from `POST /api/v1/webhook/message`. Backend work is synchronous and finished before n8n acts.

### Backend response contract n8n consumes

| Field | Required | Purpose |
|-------|----------|---------|
| `success` | yes | Branch on failure |
| `data.reply_to_customer` | yes | Customer reply workflow |
| `data.lead_created` | yes | Optional analytics / CRM branch |
| `data.lead_updated` | yes (T12 add) | Distinguish update vs create |
| `data.notify_owner` | yes | **Gate** notification workflow |
| `data.lead` | when lead touched | `{ id, status, priority, service_requested?, source_channel? }` |
| `data.notification` | when `notify_owner=true` | Normalized event per `notification-flow.md` §9 |
| `data.conversation` | yes | Existing |
| `data.message` | yes | Includes `is_duplicate` |

**Do not expose in API:** system prompts, `final_prompt`, API keys, full `raw_payload`.

### Example — new lead

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Hello! What time works for you?",
    "lead_created": true,
    "lead_updated": false,
    "notify_owner": true,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "new",
      "priority": "normal",
      "service_requested": null,
      "source_channel": "whatsapp"
    },
    "notification": {
      "type": "new_lead",
      "priority": "normal",
      "tenant_id": "...",
      "business_id": "...",
      "conversation_id": "...",
      "lead_id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "customer_name": "John",
      "customer_phone": "+41790000000",
      "message_preview": "Hello, can I book tomorrow?",
      "channel": "whatsapp",
      "created_at": "2026-05-21T10:00:00Z"
    },
    "conversation": { "id": "...", "status": "open" },
    "message": { "id": "...", "is_duplicate": false }
  }
}
```

### n8n workflow order (design reference only)

```text
POST backend → IF success → send reply_to_customer → IF notify_owner → notification workflow
```

n8n workflow JSON changes are **not** part of T12 implementation.

### What n8n must not decide itself

- Whether to create or update a lead  
- Lead dedup or status transitions  
- Whether the owner should be notified (only read `notify_owner`)  
- Lead qualification or priority (read from `lead` / `notification`)  
- AI escalation or fallback policy  

---

## Spec gaps (approval needed)

| Gap | Recommendation |
|-----|----------------|
| `lead_updated` missing from current webhook route | Add in T12.5 |
| `notification` object missing from current route | Add in T12.5 when `notify_owner=true` |
| `handoff_required` not in `AiReplyResult` | MVP: keyword heuristic + `ai_failure`; structured flag → follow-up |
| `routing.destination_*` in lead examples | Defer — no CRM in T12 |
| `is_ai_active=false` | Defer detail to T12.6 |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Lead write on duplicate | Gate on `is_duplicate=false` — T12.7 |
| Double notify on retry | `notify_owner=false` on duplicate |
| Repository layer creep | `LeadService` + `AsyncSession` only |
| Over-engineered intent classifier | First-message rule (§2) |

---

## Recommended first implementation subtask

**T12.1** — `leads` Alembic migration + `Lead` model per `database-schema.md` §9.
