**Doc status:** archived  
**Tier:** ops/archived (pending move)

# Post–T13.5 stabilization (before T14)

**Purpose:** Freeze the working test + owner-notify slice before live Telegram **customer** ingress.  
**Scope:** Git, workflow export hygiene, backups — **no workflow redesign**, no T13.6, no customer Trigger yet.

**Gate 2 evidence:** [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) § T13.5 runtime (exec 50/51/52).

---

## When to run

Complete these steps **before** any T14 implementation (Telegram customer Trigger). Human operator executes git/tag steps; agent does not commit unless explicitly asked.

---

## Checklist

### 1. Commit T13.5

- [ ] Review diff: workflow export, ops docs, **no** `.env`, no tokens in JSON.
- [ ] Commit message describes T13.5 owner notify + shaped customer reply + Gate 2 verification (docs reference only in commit body — no secret values).
- [ ] Do **not** commit `n8n/.env`, execution dumps, or credential-filled exports.

**Suggested paths in commit:**

- `n8n/workflows/t13_workflow1_test_webhook_skeleton.json` (or current canonical export name)
- `docs/ops/n8n-workflow1-test-webhook.md`
- `docs/project-status/completed.md` / `next-steps.md` if updated

### 2. Tag / snapshot workflow export

- [ ] Git tag example: `n8n-t13.5-gate2-2026-05-25` on the commit that contains the verified export.
- [ ] Tag message: pointer to Gate 2 doc section (no tokens).

### 3. Backup working workflow

- [ ] Export active workflow from n8n UI (JSON).
- [ ] Store outside repo or in `n8n/workflows/backups/` **only if** export is scrubbed (no credential secret values; credential **IDs** may be stripped).
- [ ] Filename pattern: `alpstein-incoming-message-test_gate2_YYYY-MM-DD.json`
- [ ] Note active workflow ID in ops log (e.g. `2qfhWKtgbDy6YeTh` — ID may change on re-import).

### 4. Repo export remains source of truth

- [ ] Canonical topology file in repo: `n8n/workflows/t13_workflow1_test_webhook_skeleton.json` (or renamed after review).
- [ ] README note in [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md): import from repo → re-bind credentials in UI.
- [ ] T13.8 optional task: automated export strip + activation README.

### 5. Runtime snapshot (no secrets in notes)

Document **names only** in ops ticket:

- [ ] `BACKEND_BASE_URL=http://172.20.0.1:8010`
- [ ] Owner notify: credential name `Telegram account`; env `TELEGRAM_CHAT_ID` present in `n8n/.env` (gitignored)
- [ ] Customer ingress: **not configured yet**

---

## Out of scope for this checklist

- T13.6 error/retry branches
- Telegram customer Trigger implementation (T14)
- Backend or DB changes
- Production deployment changes

---

## After stabilization

Proceed to [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md) — **T14.1** mapping spec first.
