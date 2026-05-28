# T-e1.6.2 — Website widget currentScript init fix

**Status:** todo  
**Date:** 2026-05-28

## Goal

Fix widget initialization so website chat renders when script runs after `DOMContentLoaded`.

## Scope

1. cache `document.currentScript` at script evaluation time
2. use cached script reference inside `createWidget()`
3. keep all payload and ID behavior unchanged

## Requirements

- no n8n changes
- no backend changes
- no endpoint changes
- no payload contract changes
- no visitor/session/message ID behavior changes

## Risks

- cached script may be null in non-standard loader contexts

## Tests

- `node --check website-widget/alpstein-chat-widget.js`
- open `http://localhost:8088/example.html` and verify widget renders

## Out of Scope

- transport, orchestration, or API changes
