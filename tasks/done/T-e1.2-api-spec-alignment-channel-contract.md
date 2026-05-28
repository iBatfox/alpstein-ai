# T-e1.2 — API/spec alignment for canonical normalized channel contract

## Status

Done (spec-only)

## Goal

Align E1.0/E1.1 canonical normalized channel contracts with API/spec documentation: field matrices, enums, idempotency, timestamps, validation, unsupported payloads. Keep Telegram and Website Chat mappings consistent with `POST /api/v1/webhook/message`.

## Delivered

- **`specs/architecture/normalized-channel-contract.md`** (canonical source of truth)
  - `NormalizedInboundMessage`, `NormalizedContact`, `NormalizedOutboundMessage` field matrices
  - `channel` and `channel_type` enums (MVP vs deferred)
  - Required vs optional fields
  - Idempotency rules (`idempotency_key` = `message.external_message_id`; `tg:` / `web:` formats)
  - Timestamp / UTC rules (`received_at` → `message.timestamp`)
  - Validation behavior (adapter + backend)
  - Unsupported payload / attachment handling
  - MVP transport mapping to webhook JSON
  - Telegram + Website Chat API alignment (§10)
  - Resolved E1.0 open questions (§11)

- **`specs/api/webhooks.md`** §7 — E1.2 summary, expanded field rules, `external_conversation_id`, text max, idempotency
- **`specs/api/api-endpoints.md`** — canonical contract cross-link
- **`specs/flows/incoming-message-flow.md`** — validation + adapter references
- **`specs/architecture/channel-source-attribution.md`** — dependency link
- **`docs/architecture/channel-ingress-contract.md`** — E1.2 status, open questions resolved
- **`docs/architecture/channel-mapping-telegram-website.md`** — E1.2 alignment, validation §5 points to spec
- **`docs/project-status/current-state.md`**, **`next-steps.md`**

## Constraints honored

- Spec/documentation only
- No runtime, backend, n8n, DB, or widget changes
- Telegram remains reference baseline
- No new channels beyond existing placeholders (`crm_webhook`, `form` catalog only)

## Acceptance

PASS:

- Canonical field matrices locked in `specs/architecture/`
- MVP webhook transport mapping explicit
- Telegram and Website Chat consistent with §7.2 / §10
- Project status updated
- Runtime unchanged

## Handoff

| Area | Suggested next slice |
|------|----------------------|
| Backend | Optional: enforce `message.text` max 16384 in Pydantic (non-breaking if already under cap) |
| n8n | Website chat normalize workflow when implementation approved |
| E1.3+ | Channel runtime integration per `next-steps.md` |
