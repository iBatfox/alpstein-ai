# T-e1.6.1 — E1.6 pre-commit reviewer fixes

**Status:** in-progress  
**Date:** 2026-05-28

## Goal

Apply only reviewer-requested fixes for E1.6 website chat runtime.

## Scope

1. enforce valid UUID-only `correlation_id` generation in widget runtime
2. validate/regenerate `correlation_id` in website-chat n8n normalize step
3. update ops doc wording for activation timing

## Requirements

- no backend changes
- no Telegram workflow changes
- no new endpoints
- no AI/orchestration changes
- no scope expansion

## Risks

- malformed UUID fallback behavior in legacy browsers
- JSON escaping errors in workflow code-node string edits

## Tests

- widget emits UUID `X-Correlation-Id` in request headers
- n8n normalize step accepts valid UUID and regenerates invalid/missing values
- ops wording equals: "Activate only after smoke checklist passes in the target environment."

## Out of Scope

- backend, API, or database changes
- non-E1.6 workflow rewrites
