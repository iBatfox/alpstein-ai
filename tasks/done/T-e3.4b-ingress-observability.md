# T-e3.4b — Ingress observability

**Status:** todo (blocked on E3.4a)

## Goal

Extend adapter APIs with ingress metrics, `ingress_status` / `delivery_status` split, `isolation_summary`.

## Design

[`docs/audits/e3-4-ingress-failure-isolation-design.md`](../../docs/audits/e3-4-ingress-failure-isolation-design.md) §4

## Requirements

- Extend `GET /observability/adapters` and detail route
- Update `specs/api/api-endpoints.md`
- No new tables
