# T-e3.6b — Spam containment

**Status:** todo (blocked on E3.6a)

## Goal

Reversible containment actions wired into webhook after E3.5 rate limit.

## Design

[`docs/audits/e3-6-anti-spam-protection-design.md`](../../docs/audits/e3-6-anti-spam-protection-design.md) §6

## Requirements

- `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false` default
- Actions: `allow`, `mark_suspicious`, `throttle`, `temporary_block`, `ignore`
- Tables: `spam_containments` (`0020`), `spam_decisions` audit (`0021` or split per migration engineer)
- Placement: after duplicate + E3.5; before E3.4 gate + AI
- Errors: `429 SPAM_THROTTLED`, `403 SPAM_CONTAINED`
- No permanent bans; no tenant-wide block
- Decision rows persist in isolated commit on reject

## Tests

- Repeated payload triggers throttle/block
- Adapter isolation
- TTL expiry allows traffic
- Duplicate skips evaluation
- E3.1–E3.5 regression green

## Out of scope

Manual release API (ops uses TTL / SQL for MVP)
