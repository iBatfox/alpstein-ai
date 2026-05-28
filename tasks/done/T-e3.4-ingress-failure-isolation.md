# T-e3.4 — Ingress failure isolation (planning)

**Status:** todo (design review)

## Goal

Deterministic ingress failure isolation between `telegram` and `website_chat` — visibility and containment without runtime redesign.

## Design

[`docs/audits/e3-4-ingress-failure-isolation-design.md`](../../docs/audits/e3-4-ingress-failure-isolation-design.md)

**Do not implement until design is approved.**

## Slices (after approval)

| Slice | Task |
|-------|------|
| E3.4a | `T-e3.4a-failure-isolation-model.md` |
| E3.4b | `T-e3.4b-ingress-observability.md` |
| E3.4c | `T-e3.4c-failure-containment-rules.md` |

## Out of scope

Queues, new containers, dashboards, n8n changes, auto-recovery, new brokers

## Acceptance

- Design approved
- Isolation summary + containment tests
- E3.1 / E3.2 / E3.3 / E2 regression green
