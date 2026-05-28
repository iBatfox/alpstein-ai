# Multi-Channel Identity Strategy (E1.4)

## 1. Purpose

Define a conservative, explainable identity strategy across channels **before** any real identity merge or CRM automation expansion.

This document sets rules for how Alpstein AI reasons about:

- channel-scoped identity (`external_user_id`, `external_conversation_id`);
- website pseudonymous identity (`visitor_id`, `session_id`);
- optional PII enrichment (`name`, `email`, `phone`);
- future CRM linkage preparation;
- confidence and ambiguity controls.

**Status:** architecture/spec only (E1.4).  
**No runtime behavior changes** in backend, n8n, database, CRM automations, or Telegram path.

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | n8n adapters (identity payload discipline), backend services (customer/conversation resolution), future CRM sync and dashboard analytics |
| **Endpoint** | Existing `POST /api/v1/webhook/message` only |
| **Request shape** | Existing normalized transport from E1.2 (`customer.*`, `message.*`, `source`, `attribution`) |
| **Auth** | Unchanged: API token n8n -> backend |
| **Tenant isolation** | `business_id` resolves tenant; identity decisions are always scoped by tenant/business/channel |
| **Core risk** | Unsafe cross-channel merging that incorrectly joins different humans |
| **Guardrail** | Prefer false negatives (do not merge) over false positives (wrong merge) |

MVP scope confirmation: this strategy supports multi-channel readiness without implementing cross-channel merge logic or new APIs.

---

## 3. Alignment sources

- [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md)
- [`channel-ingress-contract.md`](channel-ingress-contract.md)
- [`channel-mapping-telegram-website.md`](channel-mapping-telegram-website.md)
- [`website-chat-architecture.md`](website-chat-architecture.md)
- [`specs/api/webhooks.md`](../../specs/api/webhooks.md)
- [`specs/architecture/channel-source-attribution.md`](../../specs/architecture/channel-source-attribution.md)

When conflicts exist, `specs/` docs are authoritative.

---

## 4. Identity concepts (canonical)

### 4.1 Transport and channel identity

| Concept | Meaning | Scope | Stability |
|---------|---------|-------|-----------|
| `external_user_id` | Adapter-provided sender identifier (`customer.external_customer_id`) | `business_id` + `channel` | Channel-dependent |
| `external_conversation_id` | Adapter thread/session identifier (`message.external_conversation_id`) | `business_id` + `channel` | Strong within thread |
| `external_message_id` | Message-level idempotency key | `business_id` | Strong for duplicate control |
| `visitor_id` | Website pseudonymous user id | Website channel only | Medium (browser/storage-dependent) |
| `session_id` | Website chat thread id | Website channel only | Strong for one session |

### 4.2 Business identity layers

| Layer | Definition | MVP behavior |
|------|------------|--------------|
| **Channel contact identity** | Identity inside one channel (`channel` + `external_user_id`) | Active and authoritative |
| **Cross-channel contact identity** | One human represented across channels | **Not implemented** in MVP |
| **CRM contact identity** | External CRM record id / contact key | Prepared as optional metadata only |
| **Lead identity** | Backend lead record tied to tenant/business conversation context | Existing behavior, no cross-channel merge rules added here |

---

## 5. Channel-specific identity rules

### 5.1 Telegram identity rules (reference baseline)

- `external_user_id` from Telegram `from.id` is treated as **strong within Telegram only**.
- `external_conversation_id` uses `tg:{chat_id}` and represents the thread context.
- `external_message_id` uses `tg:{chat_id}:{message_id}` for idempotency.
- Missing phone/email does **not** weaken Telegram identity validity.
- Telegram identity must **not** auto-link to website or CRM identity without explicit future merge workflow.

### 5.2 Website anonymous identity rules

- `visitor_id` is pseudonymous and required for website chat normalization.
- `session_id` defines the conversation thread and routes outbound replies.
- `external_message_id` uses `web:{session_id}:{message_id}`.
- `visitor_id` is weaker than Telegram `from.id` because storage resets and multi-user devices are possible.
- Anonymous website chat is valid without name/email/phone.

---

## 6. Anonymous -> identified transition

Website chat may start anonymous and later receive optional PII.

### 6.1 Allowed transition pattern

1. Start with `visitor_id`-based channel contact.
2. Collect optional `name`, `email`, `phone` when user provides.
3. Enrich the same channel contact context for that session/customer timeline.
4. Keep identity decisions conservative: enrichment is not auto-merge across channels.

### 6.2 Explicit non-goals

- Do not replace channel identity with email/phone as a global primary key in MVP.
- Do not retroactively merge Telegram and website customers automatically.
- Do not trigger CRM write-back logic from enrichment alone.

---

## 7. Optional PII handling rules

| Field | Optional | Role | Merge impact in MVP |
|-------|----------|------|---------------------|
| `name` | yes | Display/context hint | None (never sufficient for merge) |
| `email` | yes | Contactability hint | Raises confidence only; no auto-merge |
| `phone` | yes | Contactability hint | Raises confidence only; no auto-merge |

Rules:

- PII can improve confidence scores (future), but cannot force merge on its own.
- Conflicting PII across records is an ambiguity signal; default is keep separate.
- Missing PII is normal and must not block processing.

---

## 8. Identity confidence model (strategy only)

Confidence is for explanation and future workflows; no runtime matching implementation in E1.4.

| Level | Meaning | Typical signals | Default action |
|-------|---------|-----------------|----------------|
| `high` | Strong channel-local confidence | Same `channel` + same `external_user_id`; stable conversation ids | Reuse within channel only |
| `medium` | Plausible but not conclusive | Matching phone/email + compatible metadata | Keep separate; flag for future review |
| `low` | Weak correlation | Name-only, locale-only, timing-only overlap | Keep separate |
| `unknown` | No reliable evidence | Sparse identifiers | Keep separate |

Explainability rule: any future merge decision must state which signals produced confidence and why alternatives were rejected.

---

## 9. Cross-channel ambiguity and non-merge policy

### 9.1 Ambiguity examples

- Same phone appears in website chat and Telegram but names differ.
- Shared family/business phone used by multiple humans.
- Reused browser/device causes same `visitor_id` for different people.
- Telegram username/profile changed over time.

### 9.2 Conservative rules

- Do **not** merge identities across channels in MVP.
- Do **not** merge based only on phone or only on email.
- Do **not** merge when conflict signals exist (different names, locales, ownership cues).
- Keep channel-local identity as source of truth until explicit merge strategy is implemented.

---

## 10. Contact identity vs CRM identity

### 10.1 Current strategy

- Alpstein channel contact identity remains backend-owned and channel-scoped.
- CRM identity is external and may be absent or stale.
- Website chat must not depend on CRM identity to function.

### 10.2 CRM linkage preparation (not implementation)

Prepare metadata fields and documentation for future controlled linkage:

- `crm_system` (e.g., HubSpot, Bitrix24)
- `crm_contact_external_id`
- `crm_lead_external_id`
- `crm_match_confidence`
- `crm_link_status` (`unlinked`, `candidate`, `linked`, `conflict`)

These are strategy artifacts only; no DB/API/runtime changes in E1.4.

---

## 11. Consent and privacy boundaries

- Anonymous messaging is allowed; consent should not require identity merge.
- Only collect minimum PII required for business communication.
- Do not expose raw identifiers or PII in public client logs.
- No secrets/tokens in identity metadata.
- Keep transport/source metadata separate from customer message text.
- Future merge flows must include explicit policy/legal review before activation.

---

## 12. Metadata retention boundaries (spec level)

Retention strategy (policy-only here):

- Keep only bounded identity metadata needed for supportability and explainability.
- Do not retain raw browser fingerprint payloads as identity keys.
- Avoid storing full raw payload for merge heuristics; use normalized fields.
- Prefer derived, bounded observability fields over free-form dumps.

This section does not introduce database retention implementation in E1.4.

---

## 13. Observability requirements for identity reasoning

Align with observability and attribution contracts:

- Log channel-scoped IDs: `channel`, `external_user_id`, `external_conversation_id`, `external_message_id`.
- Preserve `correlation_id` per inbound webhook flow.
- Include `source.platform` for attribution context (e.g., `telegram_bot_api`, `web_widget_v1`).
- Capture merge-related diagnostics as **non-decision metadata** only (e.g., confidence hints), not as runtime merge actions.
- Never log sensitive secrets or full PII payloads at unsafe verbosity levels.

---

## 14. Future-proofing by channel (strategy only)

| Channel | Identity baseline | Risk | Future merge note |
|---------|-------------------|------|-------------------|
| Telegram | `from.id` strong in-channel | Account ownership assumptions | Candidate for explicit consented linkage only |
| Website chat | `visitor_id` pseudonymous | Storage reset/shared devices | Needs cautious linkage rules |
| WhatsApp | Provider user/phone identifiers | Shared numbers/business accounts | Do not assume one phone = one human |
| Instagram | Platform account/thread ids | Alias/account sharing | Channel-scoped first |
| Forms | Email/phone optional text submissions | Spoofed contact data | Verification needed before linkage |
| CRM webhook | External CRM ids | Drift/out-of-sync states | Treat CRM id as external reference, not absolute truth |

---

## 15. Decision table: when NOT to merge

Never merge (future strategy enforcement target) when any of the following is true:

1. Different channels with only one weak matching signal.
2. Phone/email matches but conflicting name or context signals.
3. Source/platform indicates shared or public identity surface.
4. Data quality is incomplete, stale, or unverified.
5. Tenant/business scope mismatch.

Default action: keep identities separate and optionally mark as `candidate` for manual/controlled future review.

---

## 16. MVP behavior statement (explicit)

For MVP and current E0/E1 runtime:

- Identity remains channel-scoped.
- Conversation reuse logic remains unchanged and channel-bound.
- No automatic cross-channel merge.
- No CRM-driven identity merge.
- Telegram runtime remains unchanged.
- Website chat runtime must follow channel-scoped identity rules once implemented.

---

## 17. Handoff (post-review, separate tasks)

| Area | Future task direction |
|------|------------------------|
| Backend | Optional identity-confidence annotations (non-merge) in internal services |
| n8n | Ensure adapter payload discipline for `external_user_id`/`external_conversation_id` |
| CRM integration | Separate design for manual/assisted linkage workflow |
| Data model | Separate migration proposal if/when confidence/link status persistence is approved |

---

## 18. Out of scope (E1.4)

- Backend identity merge implementation
- n8n merge workflows
- DB migrations or new identity tables
- CRM automation expansion
- New endpoints
- Changes to Telegram runtime behavior
- Mandatory PII requirements for website chat

---

## 19. Document history

| Version | Task | Notes |
|---------|------|-------|
| E1.4 | T-e1.4 | Conservative multi-channel identity strategy defined before runtime merge work |
