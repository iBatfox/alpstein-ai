# T-e1.6.3 — Widget script discovery fallback

**Status:** todo  
**Date:** 2026-05-28

## Goal

Stabilize website widget script element discovery across execution contexts.

## Scope

1. keep `var widgetScript = document.currentScript;`
2. add fallback to last script tag when `widgetScript` is missing
3. keep `createWidget()` using `widgetScript`

## Requirements

- no payload changes
- no endpoint changes
- no n8n/backend changes
- no CSS redesign
- no architectural changes

## Risks

- selecting last script tag can be incorrect if additional scripts append after widget

## Tests

- `node --check website-widget/alpstein-chat-widget.js`
- open `http://localhost:8088/example.html` and verify widget renders

## Out of Scope

- any transport or orchestration changes
