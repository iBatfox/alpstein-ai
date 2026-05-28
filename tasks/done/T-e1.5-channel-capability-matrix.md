# T-e1.5 — Channel capability matrix (spec-only)

## Status

Done (spec-only)

## Goal

Document channel capabilities, limitations, and operational differences before Website Chat MVP runtime implementation to prevent unsafe assumptions across channels.

## Delivered

- **`docs/architecture/channel-capability-matrix.md`**
  - Telegram vs Website Chat capability matrix
  - Dimensions: identity strength, conversation model, id quality, delivery, webhook/retries, idempotency, attachments, limits, threading, outbound routing, rate limits, anti-spam, moderation, observability, owner notification, CRM readiness, risks, MVP support level
  - Detailed operational sub-matrices (identity, reliability, media/threading, security/moderation, observability)
  - Future placeholders only: WhatsApp, Instagram, CRM webhook, forms (explicitly non-implemented)
  - MVP guardrails and implementation boundary guidance

- **`docs/project-status/current-state.md`**, **`next-steps.md`**

## Constraints honored

- Documentation/spec only
- No backend code
- No n8n workflow changes
- No DB migrations
- No widget implementation
- No API endpoint changes
- Telegram runtime unchanged
- No support claims for future placeholder channels

## Acceptance

PASS:

- Matrix exposes Telegram vs Website operational differences clearly
- Website Chat remains planned expansion, not runtime-claimed
- Future channels clearly marked placeholder only
- Text-only MVP and no identity-merge constraints remain explicit

## Handoff

| Area | Next task direction |
|------|----------------------|
| Website Chat runtime | Use matrix + E1.3/E1.4 rules for E1.6 bounded implementation |
| Future channels | Require dedicated design + review before any support claim |
