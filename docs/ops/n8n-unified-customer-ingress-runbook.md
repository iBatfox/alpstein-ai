# Unified customer ingress — operations runbook (E1.7)

**Status:** **E1.9 production cutover complete** (PASS WITH NOTES)  
**Audience:** n8n operator / integration engineer  
**Audits:** [`e1-9-unified-ingress-cutover-2026-05-28.md`](../audits/e1-9-unified-ingress-cutover-2026-05-28.md) · [`e1-8-unified-ingress-inactive-implementation-2026-05-28.md`](../audits/e1-8-unified-ingress-inactive-implementation-2026-05-28.md) · [`telegram-incident-2026-05-29.md`](../audits/telegram-incident-2026-05-29.md)  
**F.2.1 ERPNext Lead tail:** [`n8n-erpnext-lead-sync.md`](n8n-erpnext-lead-sync.md) · audit [`f2-1-erpnext-lead-n8n-sync.md`](../audits/f2-1-erpnext-lead-n8n-sync.md)

---

## 1. Purpose

Operational reference for workflow **`alpstein-customer-ingress`** — **single production customer ingress** on `alpstein_n8n_compose`.

**Current production (post E1.9):**

| Workflow | Runtime ID | Ingress | Notes |
|----------|------------|---------|--------|
| **`alpstein-customer-ingress`** | **`aYrRmAGKhP4TJbG9`** | **ACTIVE** | Telegram + Website unified pipeline |
| Telegram webhook | — | `…/webhook/alpstein-telegram-customer-trigger-unified-inactive/webhook` | Customer bot `alpsteinai_0001bot` |
| Website webhook | — | `…/webhook/alpstein/unified-customer-ingress/website-chat/incoming` | Kill switch: `ALPSTEIN_WEBSITE_CHAT_ENABLED` |
| `alpstein-incoming-message-telegram-archived-e1-9` | `2lMuaSWD1XFOXLEK` | inactive / archived | Rollback only |
| `alpstein-incoming-message-website-chat-archived-e1-9` | `hAJ3TFYn69in0vd5` | inactive / archived | Webhook path moved to `alpstein/archived-e1-9/…` |

---

**Post-E2 follow-up:** n8n delivery PATCH wired in repo — [`delivery-outcome-patching.md`](../n8n/delivery-outcome-patching.md) (`e2-delivery-outcome-patch-v1`). Operator: observability UUID env + re-import.

---

## E2 delivery PATCH (n8n)

See [`delivery-outcome-patching.md`](../n8n/delivery-outcome-patching.md) for rollout and rollback.

---

## E1.9 production cutover (done)

| Item | Value |
|------|--------|
| Verdict | **PASS WITH NOTES** |
| Active ingress | **`aYrRmAGKhP4TJbG9`** only (+ test workflow) |
| Website widget (repo example) | `website-widget/example.html` → unified path |
| Legacy prod Website path | **500** (no owner — do not use) |
| Backups | [`docs/ops/backups/e1-9-cutover-2026-05-28/`](../ops/backups/e1-9-cutover-2026-05-28/) |

**Post-cutover operator action:** Confirm live Telegram DM to customer bot; update any deployed widgets to unified Website URL.

---

## E1.8 implementation (inactive import — done)

| Item | Value |
|------|--------|
| Export file | `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json` |
| `versionId` | `e1.8-unified-customer-ingress-v1` |
| Runtime ID | `aYrRmAGKhP4TJbG9` |
| Telegram `webhookId` | `alpstein-telegram-customer-trigger-unified-inactive` |
| Website path | `alpstein/unified-customer-ingress/website-chat/incoming` |
| Import | `docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e1_8_unified_import.json` |

**Pre-cutover credential check:** After import, re-bind **customer** bot (`alpsteinai_0001bot`) on Telegram Trigger + Telegram Send Message if n8n mapped owner bot.

**Inactive webhook probe (2026-05-28):** Unified path → **404**; production `alpstein/website-chat/incoming` → **200**.

---

## 2. Preconditions

- [ ] Design doc [`unified-customer-ingress-workflow.md`](../architecture/unified-customer-ingress-workflow.md) reviewed
- [ ] `recovery-runtime-stable-2026-05-28` tag present on baseline
- [ ] Backend health: `GET http://backend:8000/api/v1/health/ready` → 200
- [ ] `N8N_BACKEND_API_TOKEN` aligned between n8n and backend
- [ ] Telegram regression reference: [`e0-telegram-regression-2026-05-28.md`](../audits/e0-telegram-regression-2026-05-28.md)

---

## 3. Environment variables (names only)

| Variable | Unified workflow | Notes |
|----------|------------------|--------|
| `BACKEND_BASE_URL` | Required | e.g. `http://backend:8000` on compose |
| `N8N_BACKEND_API_TOKEN` | Required | Header `X-Alpstein-Webhook-Token` |
| `ALPSTEIN_TELEGRAM_BUSINESS_ID` | Per-branch default | Fallback `alpstein_ai_demo_001` |
| `ALPSTEIN_WEBSITE_CHAT_BUSINESS_ID` | Website normalize | Required on Website payload if not in body |
| `ALPSTEIN_WEBSITE_CHAT_ENABLED` | Website branch only | Exact string `true` to enable; default `false` |
| `TELEGRAM_CHAT_ID` | Owner notify only | Not customer path |
| Telegram / owner credentials | Unchanged | `alpsteinai_0001bot`, `AlpsteinAIbot` |

Optional future:

| Variable | Purpose |
|----------|---------|
| `ALPSTEIN_CUSTOMER_INGRESS_BUSINESS_ID` | Single override for both ingress branches (implementation task) |

### n8n 2.x environment variable access

**Requirement:**

```text
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
```

**Reason:** Unified ingress workflows use **Code** nodes that read `$env.*` (e.g. `ALPSTEIN_TELEGRAM_BUSINESS_ID` in **Normalize Telegram Incoming**). n8n **2.x** blocks `$env` in nodes when this flag is unset or `true`.

**Where to set:**

| Location | Notes |
|----------|--------|
| Root [`docker-compose.yml`](../../docker-compose.yml) | `n8n` service `environment:` (canonical for portable stack) |
| [`n8n/.env`](../../n8n/.env) | Must match compose after container recreate |

**Verification command:**

```bash
docker exec alpstein_n8n_compose env | grep N8N_BLOCK_ENV_ACCESS_IN_NODE
```

**Expected:**

```text
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
```

If missing or `true`, recreate the n8n container after fixing compose/env. See incident [`telegram-incident-2026-05-29.md`](../audits/telegram-incident-2026-05-29.md).

---

## 4. Build unified workflow (inactive)

1. Export/import canonical JSON from repo:
   - Target name: `alpstein-customer-ingress`
   - File: `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json`
   - Regenerate: `python3 scripts/n8n/build_e1_8_unified_workflow.py`

2. In n8n UI or CLI:
   - Bind credentials: customer bot on Telegram Trigger; owner bot on Telegram Owner Notify
   - Set workflow **inactive**

3. Configure env on n8n instance (compose or legacy):
   - `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` until deliberate enable test

4. **Do not** register production webhooks for unified workflow until cutover plan approved.

---

## 5. Verification before cutover (inactive unified workflow)

| Test | Method | Pass criteria |
|------|--------|---------------|
| Export scrub | `scripts/n8n/export-scrub.sh` | G-EXP-2 pass |
| Test channel normalize | Synthetic Telegram inject + test webhook POST | Same backend fields as current Telegram path |
| Website kill switch off | POST Website webhook with `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` | HTTP 503, `WEBSITE_CHAT_DISABLED`, no POST Backend execution |
| Website kill switch on | POST with `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` | HTTP 200, `success: true`, POST Backend in execution |
| Owner notify guard | Synthetic payload with `notify_owner: true` | Owner branch runs; no customer reply required for notify-only test |

Compare execution data: `operator_business_context` present on unified path when enabled.

---

## 6. Cutover procedure (maintenance window)

**Order matters.** Telegram is reference — validate Telegram first, then Website.

| Step | Action | Rollback if failed |
|------|--------|-------------------|
| 1 | Announce maintenance window | N/A |
| 2 | Import unified workflow **inactive** | Delete import |
| 3 | Run §5 verification on unified (inactive) | N/A |
| 4 | **Activate** unified workflow | Deactivate unified |
| 5 | Point **Telegram** provider webhook to unified workflow registration | Re-point webhook to `2lMuaSWD1XFOXLEK` (see registry) |
| 6 | Smoke: real Telegram DM to `@alpsteinai_0001bot` | Step 10 |
| 7 | Smoke: Website POST with `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` | Step 10 |
| 8 | **Deactivate** `alpstein-incoming-message-telegram` | Reactivate old Telegram workflow |
| 9 | **Deactivate** `alpstein-incoming-message-website-chat` | Reactivate old Website workflow |
| 10 | Update [`runtime-registry.md`](../../n8n/workflows/runtime-registry.md) | Restore registry entries |
| 11 | Monitor 24h; keep kill switch env documented | Set `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` if emergency off |

**Do not** run both old and new production ingress workflows active for the same channel.

---

## 7. Rollback procedure

| Trigger | Action |
|---------|--------|
| Unified misbehaves immediately after cutover | Deactivate unified; reactivate Telegram + Website workflows; restore webhook registrations per registry |
| Operator context wrong | Update Add Business Context text only; redeploy workflow import |
| Website stuck disabled | Set `ALPSTEIN_WEBSITE_CHAT_ENABLED=true`; restart n8n |
| Need full revert | Restore workflow JSON from git tag `recovery-runtime-stable-2026-05-28` or prior `versionId` |

No database rollback required.

---

## 8. Post-cutover checklist

- [ ] Only one active workflow owns Telegram customer webhook path
- [ ] Only one active workflow owns Website Chat webhook path
- [ ] POST payloads include `operator_business_context` for both channels
- [ ] Website kill switch documented and tested
- [ ] E0 Telegram regression checklist still passes on reference channel
- [ ] Old workflows archived/inactive in registry with note

---

## 9. Related tasks

| Task | Location |
|------|----------|
| E1.7 design | [`tasks/done/T-e1.7-unified-customer-ingress-workflow-design.md`](../../tasks/done/T-e1.7-unified-customer-ingress-workflow-design.md) |
| Implementation (future) | TBD — `T-e1.8-implement-unified-customer-ingress-workflow` or similar |
| E0 reference | [`tasks/done/T-e0-telegram-reference-channel-remediation.md`](../../tasks/done/T-e0-telegram-reference-channel-remediation.md) |

---

## 10. Incident recovery — Telegram webhook (n8n 2.x)

Use after n8n upgrade, container recreate, or “bot not responding” with healthy backend.

### Telegram webhook recovery

| Step | Action |
|------|--------|
| 1 | **Verify webhook registration** — Telegram Bot API `getWebhookInfo` for the **customer** bot (via n8n credential test or operator tooling). **Pass:** `url` is non-empty and points at production n8n HTTPS webhook path for unified ingress. **Fail:** empty `url` → continue steps 2–5. |
| 2 | **Unpublish** workflow `alpstein-customer-ingress` (deactivate in n8n UI) |
| 3 | **Restart** n8n: `docker restart alpstein_n8n_compose` (or `docker compose -p alpstein-ai restart n8n`) |
| 4 | **Publish** workflow (activate) — re-registers Telegram webhook |
| 5 | **Restart** n8n again (operator practice from INC-2026-05-29) |
| 6 | **Verify webhook registration** — repeat `getWebhookInfo` |
| 7 | **Send live Telegram DM** to customer bot (`@alpsteinai_0001bot` or current prod bot) |
| 8 | **Verify execution in n8n** — success path through **Normalize Telegram Incoming** → **POST Backend**; record execution ID in ops notes (not message text) |

**Also verify** §3 `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` before closing incident.

**Synthetic check (optional):** POST to unified Telegram webhook test path per [`runtime-map.md`](runtime-map.md) — expect **HTTP 200** and backend readiness unchanged.

**Full incident write-up:** [`telegram-incident-2026-05-29.md`](../audits/telegram-incident-2026-05-29.md).
