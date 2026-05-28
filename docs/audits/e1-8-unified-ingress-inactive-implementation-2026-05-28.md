# E1.8 — Unified customer ingress (inactive implementation)

**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**  
**Design:** [`unified-customer-ingress-workflow.md`](../architecture/unified-customer-ingress-workflow.md)

---

## Scope

Build and import workflow **`alpstein-customer-ingress`** **inactive** on `alpstein_n8n_compose`. No production cutover, no activation, no deactivation of existing ingress workflows.

---

## Deliverables

| Artifact | Path |
|----------|------|
| Workflow export | `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json` |
| Generator (maintainability) | `scripts/n8n/build_e1_8_unified_workflow.py` |
| Export gate | `scripts/n8n/export-scrub.sh` — `e1_8` canonical entry |
| Runbook | `docs/ops/n8n-unified-customer-ingress-runbook.md` (E1.8 section) |
| Registry | `n8n/workflows/runtime-registry.md` |

---

## Runtime evidence

| Check | Result |
|-------|--------|
| JSON valid | **PASS** — `python3 -m json.tool` |
| G-EXP-2 export-scrub | **PASS** (5 canonical files) |
| Import | **PASS** — `n8n import:workflow` on `alpstein_n8n_compose` |
| Imported workflow ID | **`aYrRmAGKhP4TJbG9`** |
| `active` after import | **`false`** (export confirms; `triggerCount: 0`) |
| In `list:workflow --active=true` | **Not listed** (unified absent) |
| Production active set unchanged | **PASS** — still `2qfhWKtgbDy6YeTh`, `2lMuaSWD1XFOXLEK`, `hAJ3TFYn69in0vd5` |
| Production Telegram `versionId` | **PASS** — `t14-alpstein-ai-greeting-v1` unchanged |
| Unified website webhook (inactive) | **PASS** — `POST …/unified-customer-ingress/website-chat/incoming` → **404** (not registered) |
| Production website webhook | **PASS** — `POST …/website-chat/incoming` → **200** (production path still owned) |
| Telegram webhook collision | **PASS** — unified `webhookId` = `alpstein-telegram-customer-trigger-unified-inactive` (distinct from prod `alpstein-telegram-customer-trigger`) |

---

## Parity checklist (repo export)

| Requirement | Status |
|-------------|--------|
| Shared **Add Business Context** | **PASS** — both normalizers → single Set node |
| `operator_business_context` in POST | **PASS** — shared `POST Backend` jsonBody |
| Shared **POST Backend** | **PASS** — one node |
| Shared **Shape Canonical Customer Reply** | **PASS** — channel branch before delivery |
| Website kill switch before normalize | **PASS** — `IF Website Chat Enabled` → 503 |
| `correlation_id` on Telegram | **PASS** — generated in normalize |
| Observability headers | **PASS** — `X-Correlation-Id`, `X-N8n-Execution-Id` on shared POST |
| `telegram_chat_id` not in POST body | **PASS** — delivery metadata only |
| Owner notify guard | **PASS** — same three-condition IF |

---

## Notes (non-blocking)

1. **Credential re-bind on import:** Runtime export shows Telegram Trigger + Telegram Send Message bound to **`AlpsteinAIbot`** (owner) instead of **`alpsteinai_0001bot`** (customer). Repo JSON specifies customer bot by name — **re-bind in n8n UI before E1.9 cutover**.
2. **No CLI execute:workflow** on this n8n version — end-to-end execution smoke deferred to E1.9 (manual execute or activate on non-prod path only).
3. **Generator script:** Re-run `python3 scripts/n8n/build_e1_8_unified_workflow.py` after changing channel normalize exports.

---

## Webhook ownership state

| Path / trigger | Owner (active) | Unified (inactive) |
|----------------|----------------|--------------------|
| Telegram provider webhook | `2lMuaSWD1XFOXLEK` | Not registered (`aYrRmAGKhP4TJbG9` inactive) |
| `alpstein/website-chat/incoming` | `hAJ3TFYn69in0vd5` | N/A |
| `alpstein/unified-customer-ingress/website-chat/incoming` | None | Reserved for E1.9 |

---

## Remaining migration risks (E1.9)

- Only one Telegram Trigger may be **active** per bot token.
- Credential re-bind after import (customer vs owner bots).
- Cutover order: activate unified → migrate Telegram webhook → smoke Telegram → migrate Website traffic → deactivate legacy workflows.
- `ALPSTEIN_WEBSITE_CHAT_ENABLED` must remain documented through cutover.

---

## E1.9 cutover sequence (exact)

1. Maintenance window announced.
2. Re-import `e1_8_unified_customer_ingress_skeleton.json` if repo changed; confirm **`active: false`**.
3. Re-bind credentials: **customer** bot on Telegram Trigger + Telegram Send Message; **owner** bot on Telegram Owner Notify.
4. Smoke unified **inactive** via n8n “Execute workflow” (Website branch synthetic item) if available — optional.
5. **Deactivate** `2lMuaSWD1XFOXLEK` and `hAJ3TFYn69in0vd5` only after unified is verified ready — **recommended order:** activate unified first, then deactivate legacy (see runbook).
6. **Activate** `aYrRmAGKhP4TJbG9` (`alpstein-customer-ingress`).
7. Point Telegram `setWebhook` to unified workflow registration URL.
8. Update widget/backend to use production website path OR switch unified webhook to production path in same window (product decision).
9. Smoke: Telegram DM + Website POST + owner notify sample.
10. Archive legacy workflows; update `runtime-registry.md`.
11. Rollback: deactivate unified, reactivate `2lMuaSWD1XFOXLEK` + `hAJ3TFYn69in0vd5`, restore Telegram webhook registration.

---

## Commands used (reference)

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
scripts/n8n/export-scrub.sh
docker cp n8n/workflows/e1_8_unified_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/e1_8_unified_import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e1_8_unified_import.json
docker exec alpstein_n8n_compose n8n list:workflow --active=true
```
