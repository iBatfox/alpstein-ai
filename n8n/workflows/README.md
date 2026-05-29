# n8n workflow exports (canonical)

**Governance:** [`docs/ops/n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md)  
**Env/credentials:** [`docs/ops/n8n-env-credential-checklist.md`](../../docs/ops/n8n-env-credential-checklist.md)  
**Repo layout (scripts):** [`docs/ops/repository-layout-n8n-scripts.md`](../../docs/ops/repository-layout-n8n-scripts.md) — export gate lives in `scripts/n8n/`; runtime scripts in `../scripts/`

Repo exports describe **topology and expressions**. Runtime activation, credentials, and Telegram webhooks are **operator-bound** after import.

---

## Directory layout

```text
n8n/workflows/
  README.md                          ← this file
  runtime-registry.md                ← runtime ID map (ops-maintained)
  t13_workflow1_test_webhook_skeleton.json
  t14_workflow_telegram_customer_ingress_skeleton.json
  e1_6_workflow_website_chat_mvp_skeleton.json
  e1_8_unified_customer_ingress_skeleton.json
  backups/                           ← dated gate snapshots only (scrubbed)
    alpstein-incoming-message-test_gate2_2026-05-25.json
```

| Path | Status |
|------|--------|
| `My_workflow.json` | **Non-canonical** — gitignored (ad-hoc UI export) |
| `backups/*` | Historical snapshots — not import targets unless rollback doc says so |

---

## Canonical exports (source of truth)

| Workflow name | File | `versionId` | Repo `active` | Ops doc |
|---------------|------|-------------|---------------|---------|
| `alpstein-incoming-message-test` | `t13_workflow1_test_webhook_skeleton.json` | `t13-5-owner-notify-v5` | `false` | [`n8n-workflow1-test-webhook.md`](../../docs/ops/n8n-workflow1-test-webhook.md) |
| `alpstein-incoming-message-telegram` | `t14_workflow_telegram_customer_ingress_skeleton.json` | `t14-alpstein-ai-greeting-v1` | `false` | [`n8n-workflow-telegram-customer-ingress.md`](../../docs/ops/n8n-workflow-telegram-customer-ingress.md) |
| `alpstein-incoming-message-website-chat` | `e1_6_workflow_website_chat_mvp_skeleton.json` | `e1.6-website-chat-mvp-v1` | `false` | [`n8n-workflow-website-chat-mvp.md`](../../docs/ops/n8n-workflow-website-chat-mvp.md) |
| `alpstein-customer-ingress` | `e1_8_unified_customer_ingress_skeleton.json` | `f2.1-erpnext-lead-sync-v1` | `false` | [`n8n-unified-customer-ingress-runbook.md`](../../docs/ops/n8n-unified-customer-ingress-runbook.md) · [`n8n-erpnext-lead-sync.md`](../../docs/ops/n8n-erpnext-lead-sync.md) |

**Rules:**

1. One canonical file per active operational path — no duplicate “skeleton” names for the same purpose.
2. Bump `versionId` on every reviewed export change (string stamp, not n8n internal UUID).
3. Keep `"active": false` in git unless deployment contract explicitly documents live activation (Contabo is ops-managed).
4. Credential blocks: **name only** — no `id` fields tied to a specific n8n instance.
5. No tokens, chat IDs, or literal `N8N_BACKEND_API_TOKEN` in JSON.

---

## Export gate (G-EXP-2)

Before committing workflow JSON:

```bash
# From repo root
scripts/n8n/export-scrub.sh
```

Optional in-place normalize (review `git diff`):

```bash
scripts/n8n/export-scrub.sh --scrub
```

See [`docs/ops/n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md) § G-EXP-2.

---

## Import (portable / clean clone)

```bash
cd /opt/alpstein-ai
docker cp n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/import.json
# Re-bind credentials in UI; do not activate until parity checklist passes
```

See [`n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md) § Safe import flow.

**Live Contabo:** do not import/activate from this README without explicit cutover task — legacy runtime stays on `n8n/docker-compose.yml`.
