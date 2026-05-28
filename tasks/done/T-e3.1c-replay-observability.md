# T-e3.1c — Replay observability

**Status:** done

## Goal

Ops-visible retry/replay activity without exposing secrets.

## Delivered

- Alembic `0014` — `replay_events`
- `ReplayEventService` + webhook/delivery wiring
- `GET /api/v1/observability/replays`
- Tests: `test_e3_1c_replay_observability.py`

## Audit

[`docs/audits/e3-1-retry-replay-protection.md`](../../docs/audits/e3-1-retry-replay-protection.md)
