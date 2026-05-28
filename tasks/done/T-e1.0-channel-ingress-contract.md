# T-e1.0 — Channel expansion scope and ingress contract

## Status

Done (spec/design only)

## Goal

Define a normalized channel ingress contract so future channels can integrate without backend rewrites.

## Delivered

- `docs/architecture/channel-ingress-contract.md`
  - channel expansion scope (near-term/later/out-of-scope)
  - `NormalizedInboundMessage`
  - `NormalizedContact`
  - `NormalizedOutboundMessage`
  - channel adapter responsibilities
  - observability/lineage requirements
  - explicit out-of-scope list
  - risks/open questions
  - next-task recommendation

## Constraints honored

- No backend implementation
- No DB migration
- No n8n workflow changes
- No new channel integration started

## Acceptance

PASS criteria satisfied:

- Telegram remains reference channel
- normalized ingress contract documented
- future channels can map into contract
- no runtime behavior changed
