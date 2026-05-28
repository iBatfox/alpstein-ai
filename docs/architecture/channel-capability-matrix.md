# Channel Capability Matrix (E1.5)

## 1. Purpose

Document operational channel capabilities and constraints before Website Chat MVP runtime work starts.

This matrix is an engineering planning artifact, not a product promise. It makes differences explicit so runtime assumptions do not leak across channels.

**Status:** spec/architecture only (E1.5).  
**No runtime changes** in backend, n8n, widget, database, or API endpoints.

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | Backend/n8n implementers, ops/release reviewers, future channel planners |
| **Core endpoint** | Existing `POST /api/v1/webhook/message` only |
| **Transport contract** | Normalized E1.2 mapping (`customer.*`, `message.*`, `source`, `attribution`) |
| **Auth** | Unchanged: API token n8n -> backend |
| **Tenant isolation** | Channel data always scoped by `business_id` and resolved tenant |
| **Risk focus** | False assumptions about identity, delivery, retries, or attachments across channels |

MVP scope confirmation: text-first messaging, no attachment-only flow, no cross-channel identity merge.

---

## 3. Alignment references

- [`channel-ingress-contract.md`](channel-ingress-contract.md)
- [`channel-mapping-telegram-website.md`](channel-mapping-telegram-website.md)
- [`website-chat-architecture.md`](website-chat-architecture.md)
- [`multi-channel-identity-strategy.md`](multi-channel-identity-strategy.md)
- [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md)
- [`specs/api/webhooks.md`](../../specs/api/webhooks.md)
- [`specs/architecture/channel-source-attribution.md`](../../specs/architecture/channel-source-attribution.md)

When conflicts exist, `specs/` docs are authoritative.

---

## 4. Capability scale

| Label | Meaning |
|------|---------|
| `implemented` | Running and validated in current runtime baseline |
| `planned` | Defined in architecture/spec; runtime not started or not released |
| `placeholder` | Reserved for future; no support claim |
| `out_of_scope_mvp` | Explicitly not supported in MVP runtime |

---

## 5. Core capability matrix (Telegram vs Website Chat)

Telegram is the reference baseline. Website Chat is the first planned expansion.

| Dimension | Telegram | Website Chat |
|-----------|----------|--------------|
| **MVP support level** | `implemented` (reference ingress baseline E0) | `planned` (E1.3 architecture; runtime not started) |
| **Identity strength** | Strong in-channel (`from.id`) | Medium/weak pseudonymous (`visitor_id`) |
| **Conversation model** | Provider chat thread (`chat.id`) | Session thread (`session_id`) |
| **Message ID quality** | Strong provider `message_id` | Variable; widget-generated `message_id` |
| **Delivery guarantees** | Provider API semantics, generally strong | Depends on widget+n8n HTTP path; weaker until hardened |
| **Webhook behavior** | Provider webhook -> n8n Telegram trigger | Widget POST -> n8n public webhook |
| **Retry semantics** | Provider/n8n retries, stable ids | Widget retry + n8n retry; must reuse same `message_id` |
| **Duplicate/idempotency** | `tg:{chat_id}:{message_id}` | `web:{session_id}:{message_id}` |
| **Attachment support** | Platform supports media, but MVP ingress is text-only | Widget attachments deferred; MVP text-only |
| **Attachment-only messages** | `out_of_scope_mvp` | `out_of_scope_mvp` |
| **Message size limits** | Adapter enforces provider constraints + E1.2 max 16384 | Widget/adapters enforce 16384 + transport guardrails |
| **Reply threading** | `chat_id` and optional `reply_to_message_id` | `session_id`, optional reply linkage |
| **Outbound routing** | n8n Telegram send API using `chat_id` | n8n returns reply to widget session transport |
| **Rate limits** | Provider limits + workflow limits | Widget throttle + edge/n8n rate limiting needed |
| **Anti-spam risk** | Bot abuse/noise, non-text updates | Higher risk: anonymous traffic, browser abuse |
| **Moderation constraints** | Provider policy + platform terms | Website policy + local abuse controls; no external platform shield |
| **Observability support** | Mature baseline from E0 + E1/E2 contracts | Planned with `web:` IDs and attribution metadata |
| **Owner notification compatibility** | Implemented via `notify_owner` flow | Planned via same `notify_owner` contract |
| **CRM linkage readiness** | Prepared only; no merge | Prepared only; no CRM dependency |
| **Cross-channel identity merge** | Not implemented | Not implemented |
| **Primary operational risks** | Chat-id mismatch, provider send errors | Visitor churn, weak ids, spam/rate pressure, timeout UX |

---

## 6. Detailed operational matrix

### 6.1 Identity and conversation semantics

| Dimension | Telegram | Website Chat | Operational note |
|-----------|----------|--------------|------------------|
| `external_user_id` source | `from.id` | `visitor_id` | Both channel-scoped only |
| `external_conversation_id` | `tg:{chat_id}` | `web:{session_id}` | Required for website adapter |
| Identity confidence | High in-channel | Medium by default | See E1.4 confidence model |
| Anonymous mode | Implicit (no phone/email) | Explicitly supported | Must not block AI response |
| Cross-channel merge | Not implemented | Not implemented | Conservative non-merge policy |

### 6.2 Reliability and idempotency

| Dimension | Telegram | Website Chat | Operational note |
|-----------|----------|--------------|------------------|
| `external_message_id` quality | Provider-generated strong key | Widget-generated or synthesized | Never POST without stable key |
| Idempotency rule | `idempotency_key == message.external_message_id` | Same rule | Locked in E1.2 |
| Duplicate handling | Stable key reuse expected | Requires strict client retry discipline | Same key on retry, new key on new send |
| Timeout profile | Provider+n8n path | Browser+n8n+backend sync path | Website more sensitive to frontend timeout UX |

### 6.3 Payload/media and threading

| Dimension | Telegram | Website Chat | Operational note |
|-----------|----------|--------------|------------------|
| Inbound payload complexity | Provider-native rich update types | Widget-native controlled JSON | Both normalize before backend |
| Attachment inbound | Deferred for MVP | Deferred for MVP | Attachment-only out of scope |
| Text requirement | Required in MVP | Required in MVP | `message.text` non-empty |
| Reply threading model | Native chat/thread ids | Session-centric thread | Adapter maps to normalized outbound |

### 6.4 Security, spam, and moderation

| Dimension | Telegram | Website Chat | Operational note |
|-----------|----------|--------------|------------------|
| Edge authentication | Provider webhook integrity model | Widget token/HMAC model (planned) | Website requires explicit edge controls |
| Anti-spam surface | Moderate | High | Anonymous browser traffic increases abuse risk |
| Rate-limit ownership | Provider + workflow | Widget + edge + n8n layers | Multi-layer limits needed for website |
| Moderation constraints | Platform policy + business policy | Business/site policy + technical safeguards | Do not assume platform pre-filtering for website |

### 6.5 Observability and operations

| Dimension | Telegram | Website Chat | Operational note |
|-----------|----------|--------------|------------------|
| Source platform label | `telegram_bot_api` | `web_widget_v1` (planned) | From attribution contract |
| Correlation support | Implemented baseline | Planned with same envelope | Reuse D1/D2 conventions |
| Owner notify compatibility | Implemented | Planned (same fields) | No new notify contract needed |
| Runbook maturity | Mature baseline docs | Architecture-only docs | Website runbooks expected post E1.6 |

---

## 7. Future channel placeholders (no support claims)

These entries are placeholders only. They are **not implemented**, **not planned for immediate runtime**, and must not be treated as available capabilities.

| Channel | Status | Identity expectation (placeholder) | Conversation expectation (placeholder) | Idempotency expectation (placeholder) | Key risk |
|---------|--------|------------------------------------|----------------------------------------|---------------------------------------|---------|
| WhatsApp | `placeholder` | Provider user/phone scoped id | Chat/thread scoped id | `wa:{phone_number_id}:{wamid}` (per E1.2) | Shared phone ownership assumptions |
| Instagram | `placeholder` | Platform account scoped id | Thread scoped id | `ig:{thread_id}:{message_id}` (per E1.2) | Account aliasing and thread mapping drift |
| CRM webhook | `placeholder` | External CRM actor/contact id | CRM event/thread reference | Adapter-defined stable external id | Upstream data quality and replay duplication |
| forms | `placeholder` | Optional submitted contact fields | Submission/session id | Adapter-defined stable submission key | Spoofed contact data and verification gaps |

No operational SLA or integration claim is implied by these placeholder rows.

---

## 8. MVP guardrails (must remain explicit)

- Telegram remains reference ingress baseline.
- Website Chat is first planned expansion; capabilities are not parity-by-default.
- Text-only MVP; attachment-only messages are out of scope.
- No cross-channel identity merge in MVP.
- No Website Chat dependency on CRM identity.
- No new endpoint design in this matrix.
- Capability descriptions are architecture and operational constraints, not marketing features.

---

## 9. Implementation boundary guidance

This matrix is used to bound E1.6 implementation decisions:

1. Reuse E1.2 normalized contract exactly.
2. Preserve channel-specific identity semantics from E1.4.
3. Do not flatten Telegram/Website differences into one behavior assumption.
4. Require explicit follow-up tasks before enabling any future placeholder channel.

---

## 10. Out of scope (E1.5)

- Backend capability implementation
- n8n workflow edits
- Widget code
- DB schema changes
- CRM automation expansion
- New endpoints or auth models
- Telegram runtime changes

---

## 11. Document history

| Version | Task | Notes |
|---------|------|-------|
| E1.5 | T-e1.5 | Channel capability matrix added for implementation planning |
