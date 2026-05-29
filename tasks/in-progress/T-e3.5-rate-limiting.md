# T-e3.5 — Rate limiting (planning)

**Status:** todo (design review)

## Goal

Backend-owned deterministic ingress rate limiting for tenant, business, adapter, and conversation scopes.

## Design

[`docs/audits/e3-5-rate-limiting-design.md`](../../docs/audits/e3-5-rate-limiting-design.md)

**Do not implement until design is approved.**

## Slices (after approval)

| Slice | Task |
|-------|------|
| E3.5a | `T-e3.5a-rate-limiting-model.md` |
| E3.5b | `T-e3.5b-rate-limit-enforcement.md` |
| E3.5c | `T-e3.5c-rate-limit-observability.md` |

## Out of scope

Redis/queues/workers, anti-spam content filtering, n8n changes, delayed requests

## Acceptance

- Design approved
- 429 enforcement + violation observability
- E3.1–E3.4 regression green
