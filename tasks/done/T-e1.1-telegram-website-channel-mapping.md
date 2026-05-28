# T-e1.1 — Telegram + Website Chat channel mapping refinement

## Status

Done (spec-only)

## Goal

Map Telegram (reference) and Website Chat (planned next) payloads into canonical E1.0 contracts:

- `NormalizedInboundMessage`
- `NormalizedContact`
- `NormalizedOutboundMessage`

## Delivered

- `docs/architecture/channel-mapping-telegram-website.md`
  - Telegram mapping tables (required/optional, fallbacks, idempotency format, unsupported payloads)
  - Website Chat mapping tables (required/optional, anonymous/session handling, metadata guidance)
  - Telegram vs Website comparison matrix
  - Adapter responsibilities and explicit non-responsibilities
  - Validation baseline and duplicate/idempotency assumptions
  - Out-of-scope list and open questions

## Constraints honored

- No backend/runtime code changes
- No n8n workflow changes
- No DB migrations
- No channel integration implementation

## Acceptance

PASS:

- Telegram mapping clear
- Website Chat mapping clear
- Both map to E1.0 canonical contract
- Risks/open questions documented
