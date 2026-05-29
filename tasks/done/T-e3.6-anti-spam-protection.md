# T-e3.6 — Anti-spam protection (planning)

**Status:** todo (design review)  
**Phase:** E3.6  
**Branch:** `stabilization/runtime-baseline`

## Goal

Backend-owned deterministic anti-spam detection and reversible containment for `telegram` and `website_chat`.

## Design

[`docs/audits/e3-6-anti-spam-protection-design.md`](../../docs/audits/e3-6-anti-spam-protection-design.md)

## Slices

| Task | Scope |
|------|--------|
| [`T-e3.6a-spam-detection-model.md`](T-e3.6a-spam-detection-model.md) | Indicators, rules, schema `0019`–`0021` |
| [`T-e3.6b-spam-containment.md`](T-e3.6b-spam-containment.md) | Enforcement, webhook wiring, 403/429 |
| [`T-e3.6c-spam-observability.md`](T-e3.6c-spam-observability.md) | List APIs, adapter metrics, specs |

## Blockers

- **Do not implement until design approved**
- E3.5d Postgres concurrency validation recommended before enabling spam flag in staging

## Out of scope

AI moderation, Redis, queues, external providers, dashboards, permanent bans, tenant-wide blocks
