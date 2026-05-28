# T-e1.6 — Website Chat MVP runtime

## Status

Done (runtime slice + docs)

## Goal

Implement the smallest Website Chat MVP runtime path using the existing normalized ingress and backend orchestration:

Widget -> n8n normalize -> `POST /api/v1/webhook/message` -> backend AI orchestration -> n8n response -> widget reply.

## Delivered

- **Website widget (text-only, embeddable)**
  - `website-widget/alpstein-chat-widget.js`
  - `website-widget/example.html`
  - `website-widget/README.md`
  - Anonymous visitor/session basics, loading state, retry-safe UX

- **n8n Website Chat adapter workflow**
  - `n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`
  - Webhook ingress + normalization + canonical `web:` IDs
  - POST backend via existing endpoint and token auth
  - Correlation propagation (`correlation_id`, `X-Correlation-Id`, `X-N8n-Execution-Id`)
  - Customer response shaping + safe error response
  - Owner notification compatibility branch (reused pattern)

- **Operational runtime docs**
  - `docs/ops/n8n-workflow-website-chat-mvp.md`
  - Startup notes, verification procedure, smoke checklist

- **Spec/doc wiring updates**
  - `docs/architecture/website-chat-architecture.md`
  - `docs/architecture/channel-capability-matrix.md`
  - `docs/ops/README.md`
  - `n8n/.env.example`
  - `docs/project-status/current-state.md`
  - `docs/project-status/next-steps.md`

## Constraints honored

- Reused existing backend orchestration path (`POST /api/v1/webhook/message`)
- Reused existing OpenAI/prompt pipeline
- Reused owner notification behavior pattern
- Reused observability model
- No new backend endpoint
- No separate AI service
- No backend architecture redesign
- No tenant model redesign
- No CRM merge logic
- No attachment/media/voice support
- Telegram runtime untouched

## Verification status

- Workflow JSON and widget assets implemented in repository
- Runtime activation/import and live smoke tests are documented as operator steps in ops runbook

## Handoff

| Area | Next action |
|------|-------------|
| Runtime ops | Import workflow, activate in n8n, execute smoke checklist |
| QA | Validate duplicate handling and owner-notify branch under website path |
| Hardening | Retry/backoff tuning, website-specific abuse controls (future slice) |
