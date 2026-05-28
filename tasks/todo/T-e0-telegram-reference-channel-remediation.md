# T-e0 — Telegram reference channel remediation (follow-up)

**Status:** todo  
**Parent gate:** [`T14.5-telegram-compose-regression.md`](../done/T14.5-telegram-compose-regression.md) · [`e0-telegram-regression-2026-05-28.md`](../docs/audits/e0-telegram-regression-2026-05-28.md)

## Goal

Close remaining E0 blockers so Telegram can be signed off as the **stable reference ingress** for Phase E multi-channel expansion.

## Blockers (from E0 continuation 2026-05-28)

| ID | Blocker | Owner |
|----|---------|--------|
| E0-R1 | `docker-compose` 1.29 + Docker 29 `ContainerConfig` — portable `n8n` service `up` fails; use documented `docker run` workaround or compose v2 | ops |
| E0-R2 | Full Telegram Trigger E2E on portable host — workflow activation + execution IDs on `alpstein_n8n_compose` with `WEBHOOK_URL` suitable for inject or live DM | ops + n8n |
| E0-R3 | Postgres volume password ↔ root `.env` alignment procedure in runbook (TCP/scram; not trust-local) | ops |
| E0-R4 | Recreate `alpstein_backend` after adding `LANGFUSE_*` to compose; verify one traced webhook | ops |
| E0-R5 | Contabo cutover plan: legacy `alpstein_n8n` (15679) vs portable `alpstein_n8n_compose` (15680); shared `alpstein_n8n_data` — no dual-writer | ops |
| E0-R6 | Legacy host backend `172.20.0.1:8010` not running — production nginx path still points at legacy n8n | ops |

## Out of scope

- WhatsApp / Instagram / CRM abstractions
- Architecture redesign

## Acceptance

- [ ] `docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d n8n` succeeds **or** runbook documents approved workaround
- [ ] One Telegram ingress smoke with **n8n execution IDs** on portable stack (`BACKEND_BASE_URL=http://backend:8000`)
- [ ] Workflow `2lMuaSWD1XFOXLEK` (or successor) deactivated post-test; registry updated
- [ ] G-EXP-2 PASS unchanged
- [ ] E0 audit verdict upgraded to **PASS** or explicit **YES WITH WARNINGS** for reference channel
