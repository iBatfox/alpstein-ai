# T-meta — Meta WhatsApp webhook verification + raw intake

## Goal

Add `GET/POST /webhooks/meta` for Meta WhatsApp Cloud API webhook verification and raw event intake (no AI, no outbound WhatsApp).

## Scope

- Config: `META_VERIFY_TOKEN` (+ WhatsApp env names in `.env.example`)
- Routes at `/webhooks/meta` (not under `/api/v1`)
- Tests + ops doc

## Out of scope

- Message normalization, n8n, AI replies, outbound WhatsApp sends
- Signature validation (`X-Hub-Signature-256`) — follow-up slice

## Tests

- GET verify success / wrong token / wrong mode
- POST valid payload / empty or invalid body
