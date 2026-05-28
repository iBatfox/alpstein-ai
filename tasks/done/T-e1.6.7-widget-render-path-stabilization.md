# T-e1.6.4 — Website widget render path deep debug

**Status:** todo  
**Date:** 2026-05-28

## Goal

Identify why website widget DOM is not appended to `document.body`.

## Scope

1. add temporary debug/warn instrumentation in widget init path
2. reproduce on local `example.html`
3. identify root cause and apply minimal frontend-only fix
4. remove noisy debug logs after fix

## Requirements

- no backend changes
- no n8n changes
- no payload/endpoint changes
- no architecture/CSS redesign
- debugging only + minimal fix

## Risks

- temporary logs may obscure signal if too noisy
- local verification may differ from production embedding contexts

## Tests

- `node --check website-widget/alpstein-chat-widget.js`
- verify widget visible in browser and in Elements DOM
- verify input and Send button visible

## Out of Scope

- transport/business logic changes
