# T-e3.3b — Adapter observability API

**Status:** todo (blocked on E3.3a)

## Goal

`GET /api/v1/observability/adapters` and `GET /api/v1/observability/adapters/{adapter}`.

## Requirements

- Webhook token auth
- Required `tenant_id`, `business_id`
- Envelope + no secrets
- Update `specs/api/api-endpoints.md`

## Design

[`docs/audits/e3-3-adapter-monitoring-design.md`](../../docs/audits/e3-3-adapter-monitoring-design.md) §5
