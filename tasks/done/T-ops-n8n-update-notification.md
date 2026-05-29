# T-ops-n8n-update-notification — n8n release notify (notify-only)

**Status:** done (O3 units + docs; host enablement pending operator evidence)  
**Phase:** Ops  
**Design:** [`docs/architecture/n8n-update-notification-service.md`](../../docs/architecture/n8n-update-notification-service.md)

## Goal

Owner receives a Telegram alert when official n8n publishes a newer release than the running `alpstein_n8n_compose` image. **No automatic update.**

## Scope

- O2: `scripts/ops/n8n_update_notify.py` + unit tests
- O3: systemd timer + [`docs/ops/n8n-update-notification-runbook.md`](../../docs/ops/n8n-update-notification-runbook.md)
- JSON state under `/var/lib/alpstein-ops/n8n-update-notify/`

## Out of scope

- docker compose pull/up
- Workflow / DB changes
- E4 `release-ctl` implementation
- Backend API routes

## Acceptance

- [x] Design reviewed
- [x] Script: GitHub latest + docker inspect + dedup + Telegram template
- [x] `--dry-run` and `--force-notify` for operators
- [x] systemd service + timer in `docs/ops/systemd/`; install documented
- [ ] Operator: first production dry-run row in runbook §7 (host)
- [x] HubSpot n8n untouched (no changes in this task)

## Tests

- `pytest scripts/ops/test_n8n_update_notify.py -v`
- Static systemd unit checks (no forbidden docker commands in units)
