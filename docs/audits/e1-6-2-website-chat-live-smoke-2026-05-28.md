# E1.6.2 — Website Chat live compose smoke verification

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Commit under test:** `169fdc3`  
**Scope:** verification-only (no backend code change, no workflow redesign, no Telegram changes)

## Final result

**Originally BLOCKED in E1.6.2, unblocked by E1.6.3 runtime stabilization**

Website Chat workflow previously failed in `Normalize Website Chat Incoming` (`Cannot find module 'crypto'`).
E1.6.3 replaced unsupported module usage with n8n-compatible UUID/hash fallback logic and reran the smoke matrix.

---

## E1.6.3 retest evidence (2026-05-28)

### Runtime patch applied

- Workflow export updated: `n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`
- `Normalize Website Chat Incoming` no longer uses `require('crypto')`
- Correlation UUID behavior preserved via:
  - `crypto.randomUUID()` when available in runtime
  - local RFC4122 v4 fallback for correlation ID only
- Existing `visitor_id` / `session_id` / `message_id` mapping preserved
- Webhook path and backend endpoint unchanged

### Retest matrix (same endpoint class as E1.6.2)

- Local: `http://127.0.0.1:15679/webhook/alpstein/website-chat/incoming`
- Public probe: `https://n8n.alpstein-ai.ch/webhook/alpstein/website-chat/incoming`

Cases executed:

1. valid payload  
2. duplicate message (`same session_id + message_id`)  
3. invalid/empty text  
4. invalid `correlation_id` in body  
5. invalid `correlation_id` via header  
6. public endpoint probe

Observed HTTP:

- valid: `200` with success body
- duplicate: `200` with success body
- invalid text: `200` (execution error on validation, no crypto error)
- invalid correlation body/header: `200` with regenerated UUID in response
- public probe: `200` with success body

Execution evidence (`workflowId=wuQM4a8vFOC1OBHB`):

```text
execution IDs: 238..243
status: success for 238,239,241,242,243
status: error for 240 (invalid text validation path)
crypto module error: absent in all executions
```

Post-smoke safety:

- Website Chat workflow deactivated again (`wuQM4a8vFOC1OBHB`)
- Active workflows unchanged for Telegram/test only

---

## 1) Pre-flight safety

| Check | Evidence | Result |
|---|---|---|
| Working tree clean | `git status -sb` showed only branch tracking line | PASS |
| Branch | `stabilization/runtime-baseline` | PASS |
| HEAD commit | `169fdc3 feat(e1): add website chat MVP runtime` | PASS |
| Compose services | `alpstein_n8n_compose`, `alpstein_backend (healthy)`, `alpstein_postgres (healthy)` running | PASS |
| HubSpot isolation | `integrationhubspot_n8n` running on `15678`, untouched | PASS |

---

## 2) Workflow import/activation

Workflow file: `n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`

Commands run:

```bash
docker cp n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json alpstein_n8n_compose:/tmp/e1_6_import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e1_6_import.json
docker exec alpstein_n8n_compose n8n update:workflow --id=OnaY83T8YLRUB8SJ --active=true
docker restart alpstein_n8n_compose
docker exec alpstein_n8n_compose n8n list:workflow --active=true
```

Runtime state after activation:

- `OnaY83T8YLRUB8SJ|alpstein-incoming-message-website-chat` active
- Telegram workflow remains active and unchanged: `2lMuaSWD1XFOXLEK`
- Test workflow remains active: `2qfhWKtgbDy6YeTh`
- Post-smoke safety: Website workflow was deactivated again (`OnaY83T8YLRUB8SJ`) because smoke is blocked.

---

## 3) Required env/config checks

| Variable | Location | Result |
|---|---|---|
| `N8N_BACKEND_API_TOKEN` | n8n + backend | Present |
| `BACKEND_BASE_URL` | n8n | Present |
| `ALPSTEIN_WEBSITE_CHAT_BUSINESS_ID` | n8n | Missing (not fatal for smoke when payload has `business_id`) |

---

## 4) Smoke matrix executed

Endpoint used:

- local compose: `http://127.0.0.1:15679/webhook/alpstein/website-chat/incoming`
- public proxy probe: `https://n8n.alpstein-ai.ch/webhook/alpstein/website-chat/incoming`

Cases sent:

1. valid `website_chat` payload  
2. duplicate message (`same session_id + message_id`)  
3. invalid/empty text  
4. invalid `correlation_id` in body  
5. invalid `correlation_id` via header  
6. public endpoint probe (widget/browser substitute)

Observed HTTP:

- all probes returned `200` with empty body

Execution evidence (n8n DB):

```text
workflowId=OnaY83T8YLRUB8SJ
execution IDs: 232..237
status: error (all)
mode: webhook
```

Failure signature captured in execution payload:

```text
VMError: Cannot find module 'crypto' [line 1]
node: Normalize Website Chat Incoming
```

Because execution fails before `POST Backend`, the following could not be verified in this run:

- backend receives `POST /api/v1/webhook/message` for website_chat
- response mapping back to widget envelope
- correlation UUID regeneration behavior at backend boundary
- `external_conversation_id` and `external_message_id` persistence
- owner-notify compatibility for Website Chat path
- backend-unavailable branch safety test (already blocked earlier in flow)

---

## 5) Telegram non-regression check

Active workflows after Website Chat activation:

- `2qfhWKtgbDy6YeTh|alpstein-incoming-message-test`
- `2lMuaSWD1XFOXLEK|alpstein-incoming-message-telegram`
- `OnaY83T8YLRUB8SJ|alpstein-incoming-message-website-chat`

No Telegram workflow mutation was performed.

---

## 6) Export/runtime parity check

Command:

```bash
scripts/n8n/export-scrub.sh
```

Result:

- `G-EXP-2: PASS (3 file(s) checked)`
- no unsafe export entered git during this verification

---

## 7) Blocking defect and next required fixes

### Blocking defect (runtime)

- **E1.6 Website Chat workflow is not operational** in current live compose runtime.
- Root blocker: n8n Code node runtime cannot resolve `crypto` in `Normalize Website Chat Incoming`.

### Required fixes before declaring operational

1. Fix workflow runtime compatibility in n8n Code node (remove unsupported module import path or use n8n-supported primitives).
2. Re-run this exact smoke matrix.
3. Confirm at least one successful execution with evidence for:
   - backend POST 200
   - duplicate handling (`is_duplicate`)
   - invalid text handling
   - correlation id behavior
   - owner notify branch behavior
   - `web:{session_id}` external IDs in persisted records

---

## Release-style summary

- **Slice:** n8n workflow verification (`E1.6.2`)  
- **Commands run:** included above  
- **Verification:** import/activation/env/smokes executed; execution evidence collected  
- **Open risks:** workflow runtime defect blocks end-to-end Website Chat  
- **Status:** **BLOCKED** until runtime compatibility fix and re-smoke

