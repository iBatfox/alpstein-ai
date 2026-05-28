# T-e1.6.6 — Website Chat activation semantics

## Status

Done (2026-05-28)

## Goal

Replace active-toggle assumption with explicit env kill switch semantics:

- `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` -> production webhook executes Website Chat flow
- `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` -> workflow returns 503 disabled response and does not call backend

## Runtime findings

- Website Chat workflow IDs discovered:
  - `hAJ3TFYn69in0vd5` (canonical)
  - `wuQM4a8vFOC1OBHB` (older canonical import)
  - `OnaY83T8YLRUB8SJ` (duplicate import)
- Production webhook path owner:
  - `alpstein/website-chat/incoming` -> `hAJ3TFYn69in0vd5`

## Duplicate handling

- Duplicate `OnaY83T8YLRUB8SJ` kept inactive
- Renamed for archive clarity:
  - `alpstein-incoming-message-website-chat-archived-e1-6-2`
- Canonical kept:
  - `hAJ3TFYn69in0vd5`
  - `alpstein-incoming-message-website-chat`

## Active/inactive verification

Production URL tested:

- `https://n8n.alpstein-ai.ch/webhook/alpstein/website-chat/incoming`

### Kill switch disabled (`ALPSTEIN_WEBSITE_CHAT_ENABLED=false`)

- Runtime response: HTTP `503`
- Body: `WEBSITE_CHAT_DISABLED`
- Execution evidence: disabled responder path used; `POST Backend` not executed

### Kill switch enabled (`ALPSTEIN_WEBSITE_CHAT_ENABLED=true`)

- Runtime response: HTTP `200`
- Execution evidence:
  - before: `258`
  - after: `259` (`success`)
  - `POST Backend` executed

## Deliverables updated

- `docs/audits/e1-6-6-website-chat-activation-semantics-2026-05-28.md`
- `docs/ops/n8n-workflow-website-chat-mvp.md`
- `n8n/workflows/runtime-registry.md`
- `n8n/.env.example`
- `docs/project-status/current-state.md`
- `docs/project-status/next-steps.md`

## Constraints check

- No backend changes
- No AI/orchestration changes
- No Telegram workflow changes
- No endpoint redesign
