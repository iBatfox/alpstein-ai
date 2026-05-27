# T14 — Switch Telegram ingress to Alpstein AI + greeting smoke test

**Status:** Done (2026-05-25)  
**Scope:** n8n workflow/runtime config, operator context, smoke test, docs — no backend/DB changes.

## Goal

Route Telegram customer ingress through `alpstein_ai_demo_001` with Alpstein AI operator business context and verify Greeting Orchestration MVP end-to-end via n8n POST path.

## Changes

| Item | Value |
|------|-------|
| `business_id` | `alpstein_ai_demo_001` |
| `operator_business_context` | Alpstein AI demo (AI assistants, CRM, automation, Telegram, multilingual, calm tone, no repeated name ask) |
| Barbershop context | Removed |
| Customer bot | `alpsteinai_0001bot` |
| Owner bot | `AlpsteinAIbot` |
| Workflow file | `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json` |
| versionId | `t14-alpstein-ai-greeting-v1` |
| Runtime workflow id | `2lMuaSWD1XFOXLEK` |

## Tests (webhook inject)

| Test | Exec | Result |
|------|------|--------|
| A — RU first contact | **89** | Pass — Russian Alpstein AI intro; no barbershop/CHF |
| B — RU follow-up | **90** | Pass — Russian CRM/Telegram help; no full intro repeat |
| C — DE first contact | **91** | Pass — German greeting + Alpstein AI intro |

**Verification:** `business_id=alpstein_ai_demo_001`, `operator_business_context` present, POST `success: true`, owner notify on A/C (backend `notify_owner`), skipped on B.

**Telegram Send:** `chat not found` (synthetic chat IDs — expected). Re-activate for real DM to `@alpsteinai_0001bot`.

**Post-test:** Runtime workflow deactivated.

## Out of scope

- Backend code, DB migrations, T13.6, OpenAI node in n8n

## Docs

- [`docs/ops/n8n-workflow-telegram-customer-ingress.md`](../../docs/ops/n8n-workflow-telegram-customer-ingress.md)
- [`docs/project-status/next-steps.md`](../../docs/project-status/next-steps.md) — T14.5 unblocked

## Gate

**T14.5 regression may start.**
