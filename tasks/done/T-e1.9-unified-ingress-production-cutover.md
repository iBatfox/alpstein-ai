# T-e1.9 — Unified customer ingress production cutover

## Status

Done (2026-05-28) — **PASS WITH NOTES**

## Goal

Move production traffic to `alpstein-customer-ingress` with rollback backups.

## Result

| Item | Value |
|------|--------|
| Unified workflow | `aYrRmAGKhP4TJbG9` — **active** |
| Archived Telegram | `2lMuaSWD1XFOXLEK` → `alpstein-incoming-message-telegram-archived-e1-9` |
| Archived Website | `hAJ3TFYn69in0vd5` → `alpstein-incoming-message-website-chat-archived-e1-9` |
| Audit | [`docs/audits/e1-9-unified-ingress-cutover-2026-05-28.md`](../../docs/audits/e1-9-unified-ingress-cutover-2026-05-28.md) |
| Backups | `n8n/workflows/backups/e1-9-cutover-2026-05-28/` |

## Constraints

- No backend/DB/compose config changes
- No workflow deletion
- Legacy deactivated only after unified smokes passed
