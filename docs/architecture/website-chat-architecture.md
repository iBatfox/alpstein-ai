# Website Chat Architecture (E1.3)

## 1. Purpose

Define the **future Website Chat ingress architecture** before implementation so runtime work (through **E1.6**) is predictable, bounded, and aligned with the Telegram reference path.

Website Chat is the **first planned channel expansion** after E0. It must:

- reuse the **same** normalized channel contract and `POST /api/v1/webhook/message` backend path as Telegram;
- keep **AI orchestration, lead logic, and persistence** in the Python backend only;
- treat n8n as the integration/normalize/delivery layer (not a second AI system).

**Status:** architecture / spec only (E1.3). **No widget, backend, n8n, or DB changes** in this document.

**Canonical contracts (locked):**

- [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md) (E1.2)
- [`channel-ingress-contract.md`](channel-ingress-contract.md) (E1.0)
- [`channel-mapping-telegram-website.md`](channel-mapping-telegram-website.md) (E1.1)
- [`multi-channel-identity-strategy.md`](multi-channel-identity-strategy.md) (E1.4)
- [`channel-capability-matrix.md`](channel-capability-matrix.md) (E1.5)
- [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7
- [`specs/flows/incoming-message-flow.md`](../../specs/flows/incoming-message-flow.md)

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | Embedded widget on tenant websites; n8n website-chat adapter; Alpstein backend (unchanged webhook); business owners (same notify path as Telegram) |
| **Ingress pattern** | Widget → **n8n public webhook** → normalize → `POST /api/v1/webhook/message` (same as Telegram) |
| **Egress pattern** | Backend `data.reply_to_customer` → n8n → **widget delivery** (sync HTTP response for MVP slice) |
| **Channel** | `channel=website_chat`, `channel_type=website_chat` |
| **Auth (widget → n8n)** | Per-deployment widget token / HMAC (edge); **not** Alpstein admin API |
| **Tenant isolation** | `business_id` on every message; backend resolves `tenant_id` |
| **AI** | Single backend AI stack — **no** widget-side LLM, **no** n8n OpenAI nodes for customer replies |
| **Risks** | Weak `message_id`; visitor/session churn; spam; PII in attribution; long sync chains timing out |

---

## 3. System boundaries

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Tenant website (browser)                                                │
│  ┌──────────────────────┐                                                │
│  │ Website Chat Widget   │  UI, session/visitor ids, page context        │
│  │ (custom JS, E1.4+)    │  No AI, no direct PostgreSQL                 │
│  └──────────┬───────────┘                                                │
└─────────────┼───────────────────────────────────────────────────────────┘
              │ HTTPS (widget-native JSON)
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  n8n — Website Chat adapter workflow (E1.5+)                             │
│  • verify widget token / signature                                       │
│  • rate-limit gate (optional Code node or reverse proxy)                 │
│  • map → NormalizedInboundMessage → POST /api/v1/webhook/message         │
│  • map backend response → widget reply payload                           │
│  • owner notify branch (same pattern as Telegram)                        │
└──────────┬──────────────────────────────────────────────────────────────┘
              │ API token
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Alpstein Backend (unchanged MVP)                                        │
│  validate → conversation → AI → lead → webhook response envelope         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Widget must not:**

- call OpenAI or hold platform prompts;
- call PostgreSQL or admin APIs;
- send raw DOM/HTML as `message.text`;
- bypass n8n to hit backend with ad-hoc shapes.

**Backend must not:**

- accept raw widget payloads without n8n normalization;
- add website-specific AI code paths (only `channel=website_chat` configuration).

---

## 4. Telegram reference vs Website Chat

| Dimension | Telegram (E0 baseline) | Website Chat (E1.3 design) |
|-----------|------------------------|----------------------------|
| Provider | Telegram Bot API | Custom widget + n8n webhook |
| Customer identity | `from.id` | `visitor_id` (browser-stable) |
| Thread key | `chat.id` | `session_id` |
| Inbound transport | Telegram → n8n trigger | Widget POST → n8n webhook |
| Outbound transport | n8n `sendMessage` | n8n → widget response (MVP: sync body) |
| Phone | Usually null | Optional PII |
| Attribution | Limited | Page URL, referrer, UTM (first message) |
| Delivery guarantee | Provider API | Sync HTTP + optional reconnect poll (later) |
| Idempotency key | `tg:{chat_id}:{message_id}` | `web:{session_id}:{message_id}` |

Behavioral parity target: **same backend outcomes** (conversation reuse, AI reply, lead, `notify_owner`).

---

## 5. Component responsibilities

### 5.1 Website Chat Widget (future — E1.4)

**Owns:**

- Render chat UI on tenant site;
- Generate/persist `visitor_id` (first-party storage);
- Generate `session_id` per chat session policy (§6);
- Generate **client** `message_id` (UUID v4 recommended) per user send;
- Collect optional PII (`name`, `email`, `phone`) only when user provides;
- Capture page context: `page_url`, `referrer`, UTM query params, `language` (browser);
- POST inbound messages to **n8n webhook URL** (configured per `business_id`);
- Display assistant replies from n8n response;
- Handle reconnect UI (§7): resume `visitor_id`, start or resume `session_id` per rules;
- Client-side send throttling (UX) in addition to server rate limits (§11).

**Does not own:**

- Business rules, lead creation, prompt assembly, owner routing logic.

### 5.2 n8n Website Chat adapter (future — E1.5)

**Owns:**

- Widget authentication verification;
- Widget JSON → logical normalized record → [`webhooks.md`](../../specs/api/webhooks.md) transport JSON;
- Prefix discipline: `web:{session_id}`, `web:{session_id}:{message_id}`;
- Map `source` / `attribution` / `message.client` per [`channel-source-attribution.md`](../../specs/architecture/channel-source-attribution.md);
- `POST /api/v1/webhook/message` with API token;
- Shape `reply_to_customer` into widget response;
- Owner notification branch when `notify_owner=true` (Telegram notify workflow pattern);
- Optional `operator_business_context` Set node (same as Telegram T14-OC-3).

**Does not own:**

- AI calls, DB writes, lead scoring logic.

### 5.3 Alpstein Backend (unchanged contract)

**Owns:** validation, tenant/business resolve, customer/conversation/message persistence, AI orchestration, lead creation, webhook response envelope.

**Website-specific config only:** `TenantChannelSetting` / AI profile for `website_chat` — not separate services.

---

## 6. Identity model: `visitor_id` and `session_id`

### 6.1 Definitions

| ID | Scope | Purpose |
|----|--------|---------|
| **`visitor_id`** | Per browser / per widget install | Stable anonymous (or identified) customer key → `customer.external_customer_id` |
| **`session_id`** | Per chat thread on site | Conversation reuse key → `message.external_conversation_id` = `web:{session_id}` |
| **`message_id`** | Per user message | Idempotency component → `message.external_message_id` = `web:{session_id}:{message_id}` |

### 6.2 Widget generation rules (recommended)

| Field | Format | Rules |
|-------|--------|-------|
| `visitor_id` | Opaque string, e.g. `v_{uuid}` | Created on first visit; stored in `localStorage` (or cookie fallback); **must** be sent on every message |
| `session_id` | Opaque string, e.g. `s_{uuid}` | New session when user opens chat after idle TTL (§7) or explicit “new conversation”; **must** be stable for the active thread |
| `message_id` | UUID v4 (client) | **Required** on every send; widget generates before POST |

**Policy:** `visitor_id` is **strictly required** from widget (no silent server generation in MVP unless a deployment explicitly documents a fallback — see E1.2 §11).

### 6.3 Backend mapping (E1.2)

| Widget / adapter | Webhook transport |
|------------------|-------------------|
| `visitor_id` | `customer.external_customer_id` |
| `session_id` (raw) | `message.external_conversation_id`: `web:{session_id}` |
| `message_id` (raw) | `message.external_message_id`: `web:{session_id}:{message_id}` |
| optional phone/email/name | `customer.phone`, `customer.email`, `customer.name` |

Conversation reuse (backend): same `tenant_id` + `business_id` + `customer_id` + `channel=website_chat` + active status — same rules as [`incoming-message-flow.md`](../../specs/flows/incoming-message-flow.md).

---

## 7. Anonymous visitors and reconnect

### 7.1 Anonymous visitors

- **First-class:** chat works with `visitor_id` only; PII optional.
- Customer record: backend find-or-create by `external_customer_id` (= `visitor_id`) when phone absent.
- Optional fields improve lead quality but **must not** block AI reply.
- Do not merge visitors across browsers (no cross-device identity in MVP).

### 7.2 Reconnect behavior

| Event | Widget behavior | Session / conversation |
|-------|-----------------|------------------------|
| Page reload, same browser | Reload `visitor_id` from storage | **Resume** `session_id` if within idle TTL; else new `session_id` |
| Idle TTL exceeded (recommended 30–120 min configurable) | Keep `visitor_id` | **New** `session_id` → new backend conversation when no reusable active thread |
| User clicks “Start over” | Keep `visitor_id` | Force new `session_id` |
| Cleared storage | New `visitor_id` | New `session_id` (new customer) |

**MVP outbound history:** widget may show only messages from current `session_id` (local cache). Loading historical DB messages via new backend read APIs is **out of scope** for E1.3/E1.6 unless separately specified.

### 7.3 Reconnect + idempotency

- Retries must reuse the same `message_id` for the same user send (widget queue).
- New user action ⇒ new `message_id`.

---

## 8. Communication model

### 8.1 Inbound (customer → AI)

```text
User types in widget
  → Widget builds widget-native payload (§9)
  → POST n8n Webhook (HTTPS, widget token)
  → n8n: validate, normalize, optional rate limit
  → POST /api/v1/webhook/message
  → Backend: full incoming-message flow
  → Response: reply_to_customer, lead_*, conversation, notify_owner
  → n8n: shape widget JSON
  → HTTP response to widget (MVP sync path)
```

**MVP recommended:** **synchronous** request/response through n8n (widget waits, shows typing indicator). Target p95 under tenant-configured timeout (suggest widget timeout **60–90s**, n8n workflow timeout aligned).

**Deferred (post–E1.6):** async accept + poll/SSE for long AI runs — requires widget edge or n8n wait-state design; not MVP slice.

### 8.2 Outbound (AI → customer)

| Step | Owner |
|------|--------|
| Text generation | Backend AI Gateway (same as Telegram) |
| Transport | n8n maps `data.reply_to_customer` to widget response field `reply.text` |
| Routing key | `session_id` in widget request echoed in response for client verification |

Logical outbound contract: `NormalizedOutboundMessage` in E1.2 — `external_conversation_id` = session routing key, `text` = AI reply.

**No** parallel push channel in E1.6 MVP unless sync path fails review; document extension in §15.

### 8.3 Widget-native payload (adapter input — not backend)

Illustrative shape for n8n adapter documentation (E1.5); **not** `POST /api/v1/webhook/message`:

```json
{
  "business_id": "demo_barbershop_001",
  "visitor_id": "v_7c9e2f1a-4b3d-4e8a-9c1f-2d6e8a0b4c3d",
  "session_id": "s_2a1b4c6d-8e9f-4012-b345-678901234567",
  "message_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "text": "Hello, do you have appointments today?",
  "timestamp": "2026-05-28T14:30:00Z",
  "name": null,
  "email": null,
  "phone": null,
  "language": "de-CH",
  "page_url": "https://example.ch/services",
  "referrer": "https://google.com/",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "spring",
  "utm_content": null,
  "utm_term": null,
  "widget_version": "1.0.0"
}
```

Adapter synthesizes `message_id` only if widget violated contract (log warning); prefer reject.

---

## 9. Message lifecycle

```text
[created]     Widget assigns message_id, timestamp (client clock → adapter normalizes UTC)
[submitted]   POST n8n webhook
[normalized]  n8n builds web:… keys
[ingested]    Backend saves customer message (or duplicate short-circuit)
[processed]   AI + optional lead
[replied]     reply_to_customer returned
[delivered]   Widget renders assistant message
[failed]      See §14 — user sees safe error string, no stack traces
```

| State | Duplicate handling |
|-------|-------------------|
| Same `web:{session_id}:{message_id}` retry | Backend idempotent skip (`is_duplicate`); widget should treat as success with same reply policy (implementation: return cached reply or generic ack — **E1.5 decision**) |
| New `message_id`, same session | New turn in same conversation if reusable |

Attachments: **unsupported** MVP — widget must not send attachment-only messages (E1.2 §9).

---

## 10. Page metadata and UTM propagation

Map to transport per [`channel-source-attribution.md`](../../specs/architecture/channel-source-attribution.md):

| Widget field | Transport target | Notes |
|--------------|------------------|-------|
| `page_url` | `attribution.landing_page_url` (first message) or update policy in adapter | Prefer first message in session only |
| `referrer` | `attribution.referrer_url` | Truncate to spec max lengths |
| `utm_*` | `attribution.utm_*` | Omit nulls |
| `language` | `source.locale` | BCP 47 |
| `widget_version` | `source.platform` = `web_widget_v1` + version in adapter metadata | Not free-form `channel` |
| `user_agent` | `message.client.user_agent` | Truncate per ATTR spec |
| IP | **Do not** send raw IP to backend in CH/EU MVP | Optional `message.client.ip_address_hash` at edge (ATTR open question) |

**Rules:**

- Never put UTM/page content in `message.text`.
- Sanitize URLs (no `javascript:` schemes); reject secret-like query params.
- Backend Prompt Builder may use bounded attribution summary (ATTR-4+); not required for E1.6 slice.

---

## 11. Anti-spam and rate limiting

Defense in **layers** (no backend business-logic change required for baseline):

| Layer | Mechanism | Owner |
|-------|-----------|--------|
| **Widget** | Disable send while in-flight; min interval between sends (e.g. 1s); max message length UI (≤16384) | E1.4 |
| **Edge / n8n** | Per `visitor_id` + per IP token bucket; max body size; reject empty/spam patterns | E1.5 / reverse proxy |
| **n8n** | Static `business_id` allowlist; widget HMAC/header secret | E1.5 |
| **Backend** | Existing validation; duplicate idempotency | unchanged |

**Recommended starting limits (tunable per deployment):**

| Limit | Value |
|-------|-------|
| Messages per `visitor_id` | 20 / minute |
| Messages per IP (hashed) | 40 / minute |
| Concurrent in-flight per `session_id` | 1 |
| Max JSON body | 64 KiB |

On limit exceeded: n8n returns **429** to widget with stable code `RATE_LIMITED` (widget-native envelope, not backend `error.code` unless request reached backend).

Honeypot/hidden field optional in widget — adapter drops if filled.

---

## 12. Observability propagation

Align with [`observability-metadata.md`](../../specs/architecture/observability-metadata.md) (D1/D2):

| Field | Source |
|-------|--------|
| `correlation_id` | Widget may send optional header `X-Correlation-Id`; else n8n or backend generates |
| `channel` | `website_chat` |
| `external_message_id` / `external_conversation_id` | Prefixed `web:…` |
| `n8n_workflow_id` / `n8n_execution_id` | n8n → backend headers when D3 enabled |
| `source_platform` | `web_widget_v1` |
| `attribution_summary` | Adapter-built one-liner from UTM (≤500 chars) |
| Langfuse tags | Include `channel:website_chat`, `business_external_id`, demo tag rules unchanged |

**Widget logging:** client-side errors only to tenant console in dev; production widget logs must not include PII or tokens.

---

## 13. Owner notification behavior

Same **backend-driven** model as Telegram ([`notification-flow.md`](../../specs/flows/notification-flow.md)):

```text
Backend sets notify_owner + lead/conversation in webhook success data
  → n8n IF notify_owner
  → Owner notify workflow (Telegram/email/Slack per tenant config)
```

Website Chat does **not** introduce a new notification type. Lead `source_channel` = `website_chat`.

**Copy hints for owner message (n8n template, not backend):** include `business_id`, lead summary, optional `attribution.utm_source` / landing page from first message metadata.

---

## 14. Failure handling and retry boundaries

| Failure zone | Who retries | Boundary |
|--------------|-------------|----------|
| Widget → n8n network | Widget | Exponential backoff, max 2 retries, **same `message_id`** |
| n8n → backend 5xx | n8n | Limited retry (e.g. 1–2) with same normalized body |
| Backend `VALIDATION_ERROR` | None | Log in n8n; return user-safe “message could not be processed” |
| Backend `BUSINESS_NOT_FOUND` | None | Misconfiguration alert |
| AI timeout / failure | Backend fallback text | Same as Telegram; `notify_owner` per existing rules |
| n8n → widget response lost | Widget | User may resend — **must** use new `message_id` unless implementing idempotent UI state machine |

**Sync timeout:** if widget times out, user may duplicate-send; stable `message_id` prevents double AI processing.

**Out of scope E1.6:** dead-letter queues, cross-region failover, offline message queue.

---

## 15. Security (architecture)

| Topic | Rule |
|-------|------|
| Widget → n8n | HTTPS only; per-site widget secret or signed payload; rotate via deployment config |
| CORS | n8n webhook endpoint allows tenant origins explicitly (not `*`) in production |
| Secrets | Never in widget bundle except **public** widget site id + webhook path token scoped to POST only |
| XSS | Widget must escape rendered assistant text |
| Backend token | n8n → backend API token unchanged; never exposed to browser |
| PII | Minimize; hash IP at edge if used |

---

## 16. Implementation phases (bounded — for E1.6 predictability)

E1.3 does **not** implement. Suggested slice order:

| Phase | Scope | Deliverable | Depends on |
|-------|--------|-------------|------------|
| **E1.4** | Widget MVP | JS bundle: visitor/session/message ids, page context, sync POST to n8n URL, render reply | E1.3 |
| **E1.5** | n8n adapter | Webhook workflow: auth, normalize, `POST /api/v1/webhook/message`, shape response, rate limit nodes | E1.2, E1.4 payload |
| **E1.6** | E2E integration | Compose/staging: one `business_id`, full loop website → n8n → backend → AI → widget + owner notify smoke; parity checklist vs Telegram | E1.4, E1.5, E0 |

**E1.6 exit criteria (recommended):**

- [ ] Inbound uses `channel=website_chat` and `web:…` idempotency keys
- [ ] Conversation reuse matches Telegram rules for same visitor + session
- [ ] Duplicate `message_id` does not double-charge AI
- [ ] `notify_owner` fires on new lead (same as Telegram path)
- [ ] Attribution fields present on first message of session
- [ ] No new backend endpoint required for core loop (sync MVP)
- [ ] Telegram regression unchanged

**Explicitly not in E1.6 unless added by separate task:** attachments, async push, cross-session history API, WhatsApp/Instagram, raw IP storage, new Alpstein public customer APIs.

---

## 17. Alignment checklist (E1.2)

| E1.2 rule | Website Chat architecture |
|-----------|---------------------------|
| `idempotency_key` = `message.external_message_id` | `web:{session_id}:{message_id}` |
| `external_conversation_id` required at adapter | `web:{session_id}` |
| `customer.phone` OR `external_customer_id` | `visitor_id` required |
| `message.text` non-empty, ≤16384 | Widget + adapter enforce |
| No raw widget payload at backend | n8n normalizes only |
| Attachments unsupported | Widget text-only MVP |

---

## 18. Out of scope (E1.3)

- Widget implementation (E1.4)
- n8n workflow JSON (E1.5)
- New `specs/api` endpoints
- DB migrations / ATTR-3 persistence
- Changing Telegram workflows
- Separate AI stack or widget-side LLM
- Live chat operator takeover UI
- File uploads / voice

---

## 19. Open questions (for E1.4–E1.6 review)

1. **Sync vs async MVP:** Is 60–90s sync acceptable for all tenants, or must E1.6 include async polling?
2. **Session idle TTL default:** 30 vs 60 vs 120 minutes?
3. **IP hash:** Required at widget edge for CH/EU (ATTR spec §422) or defer?
4. **Duplicate retry UX:** Return last AI text on duplicate `message_id` vs generic “already sent”?
5. **Historical messages:** Local-only widget history vs future `GET` conversation API?

---

## 20. Document history

| Version | Task | Notes |
|---------|------|-------|
| E1.3 | T-e1.3 | Website Chat architecture before E1.4–E1.6 implementation |
