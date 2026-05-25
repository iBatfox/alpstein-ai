# Next Steps

## Immediate: post–T13.5 stabilization (before any T14 code)

Complete human-operated checklist — **no new implementation slices until done:**

[`docs/ops/post-t13-5-stabilization.md`](../ops/post-t13-5-stabilization.md)

| Step | Action |
|------|--------|
| STAB-1 | Commit T13.5 verified slice (no secrets in diff) |
| STAB-2 | Git tag snapshot (e.g. `n8n-t13.5-gate2-2026-05-25`) |
| STAB-3 | Backup scrubbed workflow export |
| STAB-4 | Confirm repo export = source of truth |

---

## T13.5 / Gate 2 — **passed** (2026-05-25)

Owner Telegram notify + post-Respond topology + duplicate suppression — see [`n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md) § T13.5 runtime.

---

## Recommended next implementation slice: **T14** (after stabilization)

**Telegram customer ingress** — separate **client-owned** bot credential from owner notify.

| Doc | Purpose |
|-----|---------|
| [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md) | Production + MVP credential model |
| [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md) | T14.1–T14.6 task breakdown |

**Topology (planned):**

```text
Telegram Trigger → Normalize Telegram Incoming → POST Backend
  → Shape Telegram Customer Reply → Telegram Send Message
  → (existing) IF notify_owner → owner Telegram (Alpstein bot)
```

**First task after STAB:** **T14.1** — Telegram update → normalized field mapping (docs only).

**Not started:** T13.6 retries/errors, live customer Trigger nodes, backend/DB changes.

---

## Deferred in T13 slice

| ID | Task |
|----|------|
| **T13.6** | Error branches + 5xx retry |
| **T13.7** | Full manual E2E — Gate 3 |
| **T13.8** | Scrubbed workflow export to repo |

---

## Infrastructure reference

| Item | Doc |
|------|-----|
| Workflow 1 + T13.5 | [`n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md) |
| Env / credentials | [`n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md) |
| n8n Docker | [`n8n-runtime-start.md`](../ops/n8n-runtime-start.md) |
| HTTPS | [`n8n-https-reverse-proxy.md`](../ops/n8n-https-reverse-proxy.md) |
