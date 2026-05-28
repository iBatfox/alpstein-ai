# T-e3.2 — Retry / dead-letter behavior (planning)

**Status:** todo (design review)

## Goal

Deterministic retry accounting and dead-letter persistence for delivery and inbound provider retries—without runtime redesign.

## Design

[`docs/audits/e3-2-retry-dead-letter-design.md`](../../docs/audits/e3-2-retry-dead-letter-design.md)

**Do not implement until design is approved.**

## Slices (after approval)

| Slice | Task file | Scope |
|-------|-----------|--------|
| E3.2a | `T-e3.2a-retry-lifecycle.md` | `retry_attempts`, delivery state machine, max retry enforcement |
| E3.2b | `T-e3.2b-dead-letter-persistence.md` | `dead_letter_events`, delivery `dead_letter` status |
| E3.2c | `T-e3.2c-retry-observability.md` | `GET /observability/retries`, `GET /observability/dead-letter` |

## Dependencies

- E3.1a/b/c merged
- Alembic head `0014`

## Out of scope

- Queue/workers, OpenAI in-request retry loop, CRM, dashboard, n8n → PostgreSQL

## Acceptance

- Design approved
- All slice tests + full pytest + E2 verifier green
- Audit doc `docs/audits/e3-2-retry-dead-letter.md` after implementation
