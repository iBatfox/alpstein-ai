# T-e3.5a — Rate limiting model

**Status:** todo (blocked on E3.5 design approval)

## Goal

`rate_limit_buckets` + `RateLimitPolicy` — scopes, fixed windows, env limits.

## Design

[`docs/audits/e3-5-rate-limiting-design.md`](../../docs/audits/e3-5-rate-limiting-design.md) §3–5

## Migrations

- `0017_rate_limit_buckets` (and violations table per approved DDL)
