# T-e1.6.3 — Website Chat runtime stabilization

## Status

Done (2026-05-28)

## Goal

Unblock Website Chat n8n runtime by removing unsupported `require('crypto')` usage in `Normalize Website Chat Incoming`.

## Scope delivered

- Updated only: `n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`
- Replaced `crypto` module dependency with n8n-safe helpers:
  - `randomUuidV4()` uses global `crypto.randomUUID()` when available
  - local RFC4122 v4 fallback via `Math.random` for correlation fallback
  - deterministic local hash helpers for message-id/ip hash fallback paths
- Preserved:
  - `visitor_id` / `session_id` / `message_id` mapping logic
  - webhook path (`alpstein/website-chat/incoming`)
  - backend endpoint (`POST /api/v1/webhook/message`)

## Runtime verification

### Import / activation

- Imported updated workflow to runtime: `wuQM4a8vFOC1OBHB`
- Activated and restarted n8n for smoke
- Deactivated post-smoke safety (Telegram/test remained active)

### Smoke matrix rerun (E1.6.2 matrix)

Cases:
1. valid payload
2. duplicate payload
3. invalid/empty text
4. invalid body correlation_id
5. invalid header correlation_id
6. public endpoint probe

Evidence:

- Execution IDs: `238..243` (`workflowId=wuQM4a8vFOC1OBHB`)
- `Cannot find module 'crypto'`: **not present**
- Success executions: `238,239,241,242,243`
- Expected validation error execution: `240` (invalid text case)

## Docs updated

- `docs/audits/e1-6-2-website-chat-live-smoke-2026-05-28.md` (retest evidence + unblock note)
- `docs/ops/n8n-workflow-website-chat-mvp.md` (runtime compatibility note)
- `docs/project-status/current-state.md` (blocker resolved state)
- `docs/project-status/next-steps.md` (E1.6 line updated)

## Constraints check

- No backend changes
- No Telegram workflow changes
- No AI/orchestration changes
- No new endpoints
- No workflow redesign
