# T13 — n8n workflow slice (implementation plan)

**Status:** in progress — T13 plan **accepted**; **T13.1–T13.5** done (incl. Gate 2 owner Telegram); **live Telegram customer ingress** next; retries in **T13.6**  
**Date:** 2026-05-24  
**Design reference:** [`docs/project-status/t13-n8n-workflow-plan.md`](../../docs/project-status/t13-n8n-workflow-plan.md) (accepted)

**Goal:** Implement n8n workflows for test-channel MVP: normalize → backend → customer reply → owner Telegram notification.

**Depends on:** T10 webhook + T10-F1 auth, T11 AI, T12 lead/notification backend (complete).

**Out of scope:** WhatsApp Cloud production workflow (T13-W* deferred), CRM routing, PostgreSQL from n8n, production deployment changes in this slice.

---

## Spec alignment

- **In MVP:** yes — `specs/mvp/mvp-scope.md` §4.1, §4.9, §4.10
- **Primary specs:** `n8n-architecture.md`, `webhooks.md`, `api-endpoints.md`, flow specs

---

## Backend contract (must match before T13.3)

```http
POST {BACKEND_BASE_URL}/api/v1/webhook/message
X-Alpstein-Webhook-Token: {N8N_BACKEND_API_TOKEN}
Content-Type: application/json
```

Success: `success`, `data.reply_to_customer`, `data.notify_owner`, `data.lead_*`, optional `data.notification`.  
Errors: `success: false`, `error.code`, `error.message`.

**`BACKEND_BASE_URL`:** set without a trailing slash (e.g. `https://alpstein-ai.ch`, not `https://alpstein-ai.ch/`) so the HTTP node URL does not become `//api/v1/...`.

---

## Gate 1 (T13.3) — **accepted**

| Status | Meaning |
|--------|---------|
| **Implementation** | **Done** — workflow export + [`docs/ops/n8n-workflow1-test-webhook.md`](../../docs/ops/n8n-workflow1-test-webhook.md) § T13.3 |
| **Gate 1 (runtime)** | **Passed** (docs sign-off 2026-05-25) |

**Verified test URL:**

```text
POST https://n8n.alpstein-ai.ch/webhook-test/alpstein/test/incoming
```

**Observed:**

- HTTP **200**, body `success: true`, non-empty `data.reply_to_customer`
- Duplicate resend (same `external_message_id`): `data.message.is_duplicate: true`, `notify_owner: false` (backend dedup; n8n passthrough)

Runtime: [`docs/ops/n8n-runtime-start.md`](../../docs/ops/n8n-runtime-start.md), HTTPS: [`docs/ops/n8n-https-reverse-proxy.md`](../../docs/ops/n8n-https-reverse-proxy.md).

**Next:** Live Telegram **customer** ingress; then **T13.6**.

---

## Task list

### P0 — Critical path

| ID | Task | Depends on | Done when | Suggested skill | Review gate |
|----|------|------------|-----------|-----------------|-------------|
| **T13.1** | Ops checklist: document env var **names** (`BACKEND_BASE_URL`, `N8N_BACKEND_API_TOKEN`, `TELEGRAM_*` placeholders); n8n credential setup steps; no values in repo | — | [`docs/ops/n8n-env-credential-checklist.md`](../../docs/ops/n8n-env-credential-checklist.md) | **alpstein-n8n-integration-engineer** | — **done** |
| **T13.2** | **Workflow 1** skeleton: Webhook trigger (test path) + **Normalize** Code/Set node → full `NormalizedWebhookMessageRequest` shape; static `business_id` from env/config; `channel: "test"` | T13.1 | [`docs/ops/n8n-workflow1-test-webhook.md`](../../docs/ops/n8n-workflow1-test-webhook.md) | **alpstein-n8n-integration-engineer** | — **done** |
| **T13.3** | HTTP Request node: POST backend, header `X-Alpstein-Webhook-Token`, timeout; safe error branch on non-2xx (**no HTTP retries** in this task) | T13.2 | Workflow export + [`docs/ops/n8n-workflow1-test-webhook.md`](../../docs/ops/n8n-workflow1-test-webhook.md) § T13.3 | **alpstein-n8n-integration-engineer** | Impl. **done**; **Gate 1 passed** |
| **T13.4** | Customer reply path: **Shape Customer Reply** → **Respond Customer Reply** (`reply_to_customer` only) | T13.3 + Gate 1 | Test caller receives shaped JSON only | **alpstein-n8n-integration-engineer** | — **done** |
| **T13.5** | **Workflow 2 branch**: IF `$('POST Backend')` notify_owner + notification → Shape Owner Notification → Telegram (`continueOnFail`) | T13.4 | Urgent/handoff triggers notify; duplicate/follow-up do not | **alpstein-n8n-integration-engineer** | **Gate 2 passed** |
| **T13.6** | Error branches: 401/403 → stop + alert; 404/400/422 → fail + log; **5xx HTTP retry** with **identical** normalized body and `external_message_id` | T13.3 | Simulated error codes + retry behavior per plan | **alpstein-n8n-integration-engineer** | — |
| **T13.7** | **Manual E2E checklist** (below) executed and signed off | T13.5, T13.6 | All checklist items pass | **alpstein-n8n-integration-engineer** + **alpstein-reviewer** | **Gate 3** |
| **T13.8** | Optional: export workflow JSON with **stripped credential IDs** + activation README (no secrets) | T13.7 | Export review finds no tokens | **alpstein-n8n-integration-engineer** | — |
| **T13.9** | Update `docs/project-status/{completed,current-state,next-steps}.md` | T13.7 | n8n marked implemented for test path | **alpstein-n8n-integration-engineer** | — |

### P2 — Deferred (WhatsApp Cloud — not scheduled)

| ID | Task | Notes |
|----|------|--------|
| **T13-W1** | Meta webhook verify + raw inbound trigger | Provider signature in n8n |
| **T13-W2** | Raw WhatsApp → normalized mapping; **`wamid` → `external_message_id`** | Per `alpstein-n8n-integration-engineer/reference.md` |
| **T13-W3** | WhatsApp Cloud API send reply node (`reply_to_customer`) | Backend still owns logic |
| **T13-W4** | WhatsApp E2E + Meta app review checklist | After W1–W3 |

**Implement T13-W* only with explicit approval** — not part of T13 P0.

---

## Workflow architecture

```text
[Webhook test]
    → Normalize
    → HTTP POST backend
    → IF success
         → Respond to Webhook (reply_to_customer)
         → IF notify_owner → Telegram notify (Workflow 2 branch)
       ELSE
         → Error handler
```

Workflow 1 + Workflow 2 may be **one workflow** with branches (MVP simplicity per `n8n-architecture.md` §15).

---

## Manual E2E checklist (T13.7)

### Prerequisites

- [ ] Backend running; `alembic upgrade head`; dev AI seed applied
- [ ] `N8N_BACKEND_API_TOKEN` set on backend and n8n HTTP header
- [ ] `BACKEND_BASE_URL` points to reachable HTTPS (or local dev URL)
- [ ] Test business `external_id` exists in DB

### Happy path — new lead

- [ ] Send test webhook with new `external_message_id`
- [ ] Backend returns `200`, `success: true`, non-empty `reply_to_customer`
- [ ] `lead_created: true`, `notify_owner: true`, `notification.notification_type: new_lead`
- [ ] Customer/test client receives reply text
- [ ] Owner Telegram message received

### Follow-up message

- [ ] Same customer, **new** `external_message_id`, second message
- [ ] `lead_updated: true`, `lead_created: false`, `notify_owner: false`
- [ ] No owner notification sent

### Duplicate retry

- [ ] Resend **same** payload + same `external_message_id`
- [ ] `message.is_duplicate: true`, `notify_owner: false`, `lead_created: false`
- [ ] Customer still gets `reply_to_customer` (prior AI text or ack)
- [ ] No second Telegram notification

### AI failure / fallback (optional)

- [ ] Force Gateway failure in dev (invalid key or mock) → fallback reply + `notification_type: ai_failure` if policy fires
- [ ] Owner notified when `notify_owner: true`

### Auth errors

- [ ] Missing/wrong token → 401, no customer reply from fabricated body
- [ ] Wrong `business_id` → 404 `BUSINESS_NOT_FOUND`

### Hygiene

- [ ] Execution logs contain no API tokens
- [ ] `external_message_id` unchanged across HTTP retries

---

## Idempotency rules (implementation)

1. Normalization **must** set `message.external_message_id` when available.  
2. HTTP retries (**T13.6** only): same JSON body and same `external_message_id`.  
3. Never branch notify on `lead_created` alone — use `notify_owner`.  
4. Never skip backend call because n8n “already saw” the message.

---

## Dependency graph

```text
T13.1 → T13.2 → T13.3 → T13.4 → T13.5
              └→ T13.6
T13.5 + T13.6 → T13.7 → T13.8 / T13.9
T13-W* — independent; explicit approval required
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Auth header mismatch | T13.3 uses `X-Alpstein-Webhook-Token` |
| Notify on duplicate | Checklist + `notify_owner` gate only |
| Secrets in workflow export | T13.8 review |
| Scope creep to WhatsApp | T13-W* deferred |

---

## Recommended next task

**Live Telegram customer ingress** — production customer webhook (owner notify done, Gate 2 passed). Then **T13.6**.
