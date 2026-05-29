# T-e3.5b — Rate limit enforcement

**Status:** todo (blocked on E3.5a)

## Goal

`RateLimitService` wired into webhook after duplicate detection; `429 RATE_LIMIT_EXCEEDED`.

## Design

[`docs/audits/e3-5-rate-limiting-design.md`](../../docs/audits/e3-5-rate-limiting-design.md) §4

## Requirements

- `ALPSTEIN_AI_RATE_LIMIT_ENABLED` default false
- Duplicates exempt from increment
- Adapter scope isolation
