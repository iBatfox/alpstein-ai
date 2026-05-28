# T-e3.3 — Adapter monitoring (planning)

**Status:** todo (design review)

## Goal

Adapter-level operational health for Telegram and Website Chat, derived from existing observability tables.

## Design

[`docs/audits/e3-3-adapter-monitoring-design.md`](../../docs/audits/e3-3-adapter-monitoring-design.md)

**Do not implement until design is approved.**

## Slices (after approval)

| Slice | Task |
|-------|------|
| E3.3a | `T-e3.3a-adapter-health-model.md` |
| E3.3b | `T-e3.3b-adapter-observability-api.md` |
| E3.3c | `T-e3.3c-operational-degradation-detection.md` |

## Out of scope

Grafana/Prometheus, dashboards, new containers, CRM, n8n → PostgreSQL, new snapshot tables (unless approved later)

## Acceptance

- Design approved
- Adapter APIs + deterministic status tests
- E2/E3.1/E3.2 regression green
