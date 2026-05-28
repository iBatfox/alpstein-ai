# T-e1.6.2 — Website Chat live smoke verification

**Status:** done (verification completed, result BLOCKED)  
**Date:** 2026-05-28  
**Audit:** `docs/audits/e1-6-2-website-chat-live-smoke-2026-05-28.md`  
**Commit verified:** `169fdc3`

## Scope

- Live compose/n8n verification only
- No backend code changes
- No workflow redesign
- No Telegram workflow changes

## Outcome

**BLOCKED**

Workflow imported and activated (`OnaY83T8YLRUB8SJ`), but all live webhook executions errored before backend call:

- `VMError: Cannot find module 'crypto' [line 1]`
- node: `Normalize Website Chat Incoming`

## Checks completed

- [x] working tree clean
- [x] compose services running
- [x] workflow imported/activated
- [x] env baseline checked (`N8N_BACKEND_API_TOKEN`, `BACKEND_BASE_URL`)
- [x] smoke matrix executed
- [x] runtime evidence captured (execution IDs 232..237, all error)
- [x] export scrub gate (`G-EXP-2`) rerun
- [x] Telegram workflow non-regression confirmed
- [x] Website workflow deactivated after blocked smoke (safe runtime state)

## Not verifiable due blocker

- [ ] backend POST path for website_chat (`/api/v1/webhook/message`) through this workflow
- [ ] duplicate semantics from backend response
- [ ] correlation UUID preserve/regenerate in successful response
- [ ] external IDs persistence verification (`web:{session_id}` patterns)
- [ ] owner notify behavior in successful website-chat flow
- [ ] backend-unavailable branch test

## Next required fix

Resolve n8n Code node runtime incompatibility (`crypto` import in workflow code), then re-run E1.6.2 smoke end-to-end.

