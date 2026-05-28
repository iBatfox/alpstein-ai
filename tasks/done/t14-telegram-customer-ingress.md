# T14 — Telegram customer ingress (implementation plan)

**Status:** todo — **blocked** until [`post-t13-5-stabilization.md`](../ops/post-t13-5-stabilization.md) complete  
**Date:** 2026-05-25  
**Credential model:** [`docs/architecture/telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md)

**Goal:** Live Telegram **customer** messages → normalize → backend → AI reply → Telegram send; reuse existing owner-notify branch (T13.5, separate bot credential).

**Depends on:** T13.1–T13.5 (Gate 1 + Gate 2 passed), T10–T12 backend.

**Out of scope:** T13.6 retries/errors, backend code, DB migrations, owner-bot redesign, WhatsApp (T13-W*).

---

## Spec alignment

- **In MVP:** partial — `mvp-scope.md` lists WhatsApp + test; Telegram architecture-ready; customer ingress is explicit next step post–Gate 2.
- **Primary specs:** `webhooks.md`, `n8n-architecture.md`, `incoming-message-flow.md`, `telegram-channel-credentials.md` (design)
- **Spec gap (approval):** Formal `tenant_channel_settings.metadata.credential_ref` contract in `database-schema.md` / `entities.md` — document before persisting refs in DB.

---

## Topology (frozen target — no redesign of T13.5)

```text
Telegram Trigger                    ← client bot credential ONLY
  → Normalize Telegram Incoming     ← channel: "telegram", external_message_id, customer ids
  → POST Backend                    ← unchanged contract
  → Shape Telegram Customer Reply   ← reply_to_customer (may extend T13.4 shape)
  → Telegram Send Message           ← same client bot credential
  → IF notify_owner (POST Backend)  ← unchanged T13.5 branch
       → Shape Owner Notification
       → Telegram Owner Notify      ← Alpstein credential ONLY
```

---

## Pre-flight (human — not agent code)

| ID | Task | Done when |
|----|------|-----------|
| **STAB-1** | Commit T13.5 + docs | Git commit on main/feature branch |
| **STAB-2** | Tag `n8n-t13.5-gate2-*` | Tag points to verified export |
| **STAB-3** | Backup scrubbed workflow JSON | Backup file stored; no tokens |
| **STAB-4** | Confirm repo export = source of truth | README in workflow doc updated |

---

## Task list (P0)

| ID | Task | Depends on | Done when | Skill |
|----|------|------------|-----------|-------|
| **T14.1** | Doc: Telegram update → normalized field mapping (`external_message_id`, `customer.external_customer_id`, chat id for send) | STAB-* | Section in ops doc + spec pointer; no workflow JSON | **alpstein-n8n-integration-engineer** |
| **T14.2** | Create **separate** n8n Telegram API credential for customer bot (name convention `telegram_customer_<business_external_id>`); verify **not** owner credential | T14.1, credential model | `getMe` test in n8n; two credentials visible | **alpstein-n8n-integration-engineer** |
| **T14.3** | Add **Telegram Trigger** + **Normalize Telegram Incoming** nodes; wire into existing POST Backend chain | T14.2, T13.5 topology | Test update reaches backend with `channel: telegram` | **alpstein-n8n-integration-engineer** |
| **T14.4** | **Telegram Send Message** after Shape Customer Reply; map `chat_id` from trigger context | T14.3 | Customer receives `reply_to_customer` in Telegram | **alpstein-n8n-integration-engineer** |
| **T14.5** | Verify owner branch still uses Alpstein credential only; duplicate + urgent regression (exec-style checklist) | T14.4 | Gate 2 behaviors unchanged | **alpstein-n8n-integration-engineer** |
| **T14.6** | Export scrubbed JSON + update ops docs; optional `tenant_channel_settings.metadata.credential_ref` in seed (reference string only) | T14.5 | **alpstein-reviewer** Gate |

**Defer:** T13.6 (retries), T13.7 full E2E, separate workflow per business automation.

---

## Manual verification (T14.6)

- [ ] New `external_message_id` per Telegram message → backend 200, reply in customer chat
- [ ] Duplicate Telegram update / retry → `is_duplicate: true`, no second owner notify
- [ ] Urgent phrase → owner Telegram via **owner** bot only
- [ ] Workflow JSON grep: no `bot_token`, no `N8N_BACKEND_API_TOKEN` literals
- [ ] Two distinct Telegram credentials in n8n UI

---

## Risks

| Risk | Mitigation |
|------|------------|
| Owner/customer credential mix-up | T14.2 naming + T14.5 regression |
| Token in committed JSON | STAB-3 + T14.6 export review |
| Wrong `external_message_id` dedup | T14.1 mapping spec |
| Breaking T13.5 topology | Add nodes; do not remove IF notify chain |

---

## Recommended next task

**STAB-1** — Commit T13.5 verified slice, then **T14.1** mapping doc before any Trigger node.
