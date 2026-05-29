# systemd units — Alpstein ops (repo copies)

Install to `/etc/systemd/system/` on the host. See [`../n8n-update-notification-runbook.md`](../n8n-update-notification-runbook.md).

| File | Purpose |
|------|---------|
| `alpstein-n8n-update-notify.service` | Oneshot: run `n8n_update_notify.py` |
| `alpstein-n8n-update-notify.timer` | Daily schedule + 30m randomized delay |
| `n8n-update-notify.env.example` | Template for `/etc/alpstein/n8n-update-notify.env` |
