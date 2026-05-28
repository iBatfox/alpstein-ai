# T-e1.3 — Website Chat architecture (spec-only)

## Status

Done (spec-only)

## Goal

Design future Website Chat ingress architecture before implementation so **E1.6** E2E work is predictable and bounded. Align with E1.0–E1.2 normalized contracts and Telegram reference path.

## Delivered

- **`docs/architecture/website-chat-architecture.md`**
  - Widget vs n8n vs backend responsibilities
  - Widget → n8n → `POST /api/v1/webhook/message` communication model (sync MVP)
  - `visitor_id` / `session_id` / `message_id` model
  - Anonymous visitor and reconnect rules
  - Outbound reply routing via n8n (no separate AI)
  - Message lifecycle
  - Page metadata / UTM → `source` / `attribution` / `message.client`
  - Anti-spam / rate limiting layers
  - Observability propagation (correlation, `web:` ids, Langfuse tags)
  - Owner notification (same `notify_owner` path as Telegram)
  - Failure / retry boundaries
  - Bounded implementation phases E1.4 → E1.5 → E1.6

- **`docs/project-status/current-state.md`**, **`next-steps.md`**

## Constraints honored

- Documentation/spec only
- No widget, backend, n8n, DB, or new API endpoints
- Telegram runtime unchanged
- Reuses normalized channel contract; single backend AI system

## Acceptance

PASS:

- Architecture doc covers all scope items from task brief
- Explicit alignment with E1.2 webhook mapping
- E1.6 exit criteria and phase boundaries documented
- Project status updated

## Handoff

| Phase | Task |
|-------|------|
| E1.4 | Widget MVP (visitor/session/message ids, sync n8n POST) |
| E1.5 | n8n website-chat adapter workflow |
| E1.6 | Compose E2E smoke + Telegram regression unchanged |
