# Channel Ingress Contract (E1.0)

## Purpose

Define a controlled, normalized ingress contract so Alpstein AI can expand beyond Telegram without backend rewrites per channel.

Telegram remains the **reference channel** baseline.

This document is **design/spec only** for Phase E1.0.

**Canonical API alignment (E1.2):** field matrices, enums, idempotency, validation — [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md). This file remains the E1.0 overview; prefer the spec path for implementation and review.

## Scope Classification

### Near-term

- Telegram (reference behavior, already active)
- Website chat (next expansion target)

### Later

- WhatsApp
- Instagram DM
- CRM-originated webhooks
- Form submissions

### Out of scope now

- Email ingress implementation
- Voice/calls implementation
- Multi-channel identity resolution engine
- CRM redesign
- Generic event bus/platform rewrite

## Canonical Contracts

### NormalizedInboundMessage

Required:

- `business_id` (string)
- `channel` (string enum — **locked in E1.2 spec** §4.1)
- `channel_type` (string enum — **locked in E1.2 spec** §4.2)
- `text` (string, may be empty only when attachment-first payload is explicitly supported later)
- `received_at` (ISO-8601 datetime)
- `idempotency_key` (string)

Optional:

- `external_user_id`
- `external_conversation_id`
- `external_message_id`
- `language`
- `attachments` (normalized list; adapter-defined subtype mapping)
- `source_metadata` (safe structured map only)
- `tenant_id` (optional at ingress; backend resolves via `business_id` in MVP)

Notes:

- Channel/source metadata must never be mixed into `text`.
- `raw_payload` remains audit/debug only and is not primary AI input.

### NormalizedContact

Required:

- `channel`
- `external_user_id` (or channel-equivalent stable sender id where available)

Optional:

- `display_name`
- `phone`
- `email`
- `username`
- `language`
- `consent_status` (future-ready, optional)
- `metadata`

Notes:

- No CRM/global identity resolution in E1.0.
- Contact matching across channels is explicitly deferred.

### NormalizedOutboundMessage

Required:

- `channel`
- `external_conversation_id`
- `text`

Optional:

- `reply_to_message_id`
- `attachments`
- `metadata`

Delivery constraints stay adapter responsibility (payload shape, rate limits, attachment constraints, retries).

## Channel Adapter Responsibility Model

Each adapter (Telegram, Website Chat, WhatsApp, Instagram, etc.) must:

- parse platform payload
- map to normalized contracts
- compute/forward `idempotency_key`
- normalize attachments
- preserve safe source metadata
- map reply target identifiers for outbound delivery

Adapters must **not** contain:

- AI orchestration/business logic
- lead logic
- CRM business rules
- direct PostgreSQL writes

## Observability Requirements (Ingress Baseline)

Every ingress record should preserve lineage fields:

- `channel`
- `external_message_id` (if present)
- `external_conversation_id` (if present)
- `idempotency_key`
- `conversation_id` (after backend resolution)
- `prompt_run_id` (after AI execution, where applicable)
- `trace_id` / `correlation_id` (when available)
- `adapter_name`
- `adapter_version`

Telegram E0 behavior is the reference baseline for required operational traceability.

## Storage Boundaries (High-level)

- Normalized fields are primary integration contract.
- `raw_payload` is debug/audit fallback only.
- Secrets/tokens/signatures are forbidden in normalized source metadata.
- External IDs are channel-scoped.

## What E1.0 Explicitly Does Not Do

- Implement WhatsApp/Instagram/website integrations
- Rewrite backend orchestration
- Change AI behavior/prompting semantics
- Change CRM automation behavior
- Replace n8n
- Introduce scaling platform/Kubernetes/event-bus architecture
- Introduce billing/product expansion

## Risks

- Adapter drift causing inconsistent normalization across channels
- Overloading `source_metadata` with unstable fields
- Incorrect idempotency strategy for channels lacking strong message IDs
- Premature identity-unification assumptions across channels

## Open Questions

Resolved in E1.2 — see [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md) §11.

## E1.1 Refinement Status

E1.1 mapping refinement is complete (spec-only):

- `docs/architecture/channel-mapping-telegram-website.md`
- `tasks/done/T-e1.1-telegram-website-channel-mapping.md`

No runtime implementation was introduced by E1.1.

## E1.2 API/spec alignment status

**Done (spec-only):**

- [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md)
- [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7 (transport mapping, validation, idempotency)
- [`tasks/done/T-e1.2-api-spec-alignment-channel-contract.md`](../../tasks/done/T-e1.2-api-spec-alignment-channel-contract.md)

Runtime unchanged. **E1.3** Website Chat architecture: [`website-chat-architecture.md`](website-chat-architecture.md). Next implementation: E1.4 widget → E1.5 n8n → E1.6 E2E.

Identity strategy baseline (E1.4): [`multi-channel-identity-strategy.md`](multi-channel-identity-strategy.md) (conservative cross-channel non-merge rules).
