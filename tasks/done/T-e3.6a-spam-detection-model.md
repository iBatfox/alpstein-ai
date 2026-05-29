# T-e3.6a — Spam detection model

**Status:** todo (blocked on E3.6 design approval)

## Goal

Deterministic spam indicators, env-configurable rules, additive schema for atomic counters.

## Design

[`docs/audits/e3-6-anti-spam-protection-design.md`](../../docs/audits/e3-6-anti-spam-protection-design.md) §4–§5

## Requirements

- Rules: `payload_repeat_conversation`, `conversation_burst`, `adapter_conversation_fanout`, derived retry rules
- `SpamPolicy` from env; no hidden scoring
- Table `spam_indicator_buckets` (migration `0019`)
- Payload fingerprint = SHA-256 of normalized text; **never** store message text in spam tables
- Idempotent duplicates exempt from increment

## Tests

- Rule threshold math unit tests
- Payload hash stability tests
- Model/metadata alignment with `database-schema.md` (after spec update on approval)

## Out of scope

Containment enforcement, HTTP routes
