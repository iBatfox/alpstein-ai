# n8n Update Notification — Operations Runbook

**Doc status:** implemented (O2 script + O3 systemd)  
**Architecture:** [`../architecture/n8n-update-notification-service.md`](../architecture/n8n-update-notification-service.md)  
**systemd units (repo):** [`systemd/`](systemd/)  
**As-of:** 2026-05-29

> **Notification only.** This does not pull images, restart containers, or change workflows. For manual updates see [`../../tasks/in-progress/T-ops-n8n-manual-update.md`](../../tasks/in-progress/T-ops-n8n-manual-update.md). For future approved deploys see [`e4-release-controller-runbook.md`](e4-release-controller-runbook.md).

---

## 1. What it does

On a schedule (default: **once daily** via systemd timer), a host script:

1. Reads the running n8n image tag from `alpstein_n8n_compose`.
2. Fetches the latest official release from GitHub (`n8n-io/n8n`).
3. Sends **one** Telegram message per new upstream version (deduped).
4. Stores state in `/var/lib/alpstein-ops/n8n-update-notify/state.json`.

---

## 2. Preconditions

- [ ] Portable stack running: `alpstein_n8n_compose` ([`runtime-map.md`](runtime-map.md))
- [ ] HubSpot n8n on **15678** — **do not modify**
- [ ] Ops Telegram bot token + owner `chat_id` (not customer ingress bot)
- [ ] `docker` available to script user (root or in `docker` group)
- [ ] Outbound HTTPS to `api.github.com` and `api.telegram.org`

---

## 3. Configuration (host only — not in git)

### 3.1 Environment file

Path: `/etc/alpstein/n8n-update-notify.env` (mode **600**, root-owned).

Template: [`systemd/n8n-update-notify.env.example`](systemd/n8n-update-notify.env.example)

| Variable | Required | Purpose |
|----------|----------|---------|
| `N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN` | **Yes** | Ops Telegram bot |
| `N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID` | **Yes** | Owner chat |
| `GITHUB_TOKEN` | No | Higher GitHub API rate limit |
| `N8N_UPDATE_NOTIFY_STATE_PATH` | No | Default: `/var/lib/alpstein-ops/n8n-update-notify/state.json` |
| `N8N_UPDATE_NOTIFY_CONTAINER` | No | Default: `alpstein_n8n_compose` |

### 3.2 State directory

```bash
sudo install -d -m 755 /etc/alpstein
sudo install -d -m 755 /var/lib/alpstein-ops/n8n-update-notify
# If the service runs as a non-root user, chown the state dir to that user.
```

---

## 4. Install systemd (O3)

From repo root on the host:

```bash
cd /opt/alpstein-ai

# Directories
sudo install -d -m 755 /etc/alpstein
sudo install -d -m 755 /var/lib/alpstein-ops/n8n-update-notify

# Env (edit tokens before enabling timer)
sudo cp docs/ops/systemd/n8n-update-notify.env.example /etc/alpstein/n8n-update-notify.env
sudo chmod 600 /etc/alpstein/n8n-update-notify.env
sudo nano /etc/alpstein/n8n-update-notify.env

# Units
sudo install -m 644 docs/ops/systemd/alpstein-n8n-update-notify.service /etc/systemd/system/
sudo install -m 644 docs/ops/systemd/alpstein-n8n-update-notify.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now alpstein-n8n-update-notify.timer
```

Verify timer:

```bash
systemctl list-timers | grep alpstein-n8n-update-notify
systemctl status alpstein-n8n-update-notify.timer --no-pager
```

Manual one-shot run (uses env file):

```bash
sudo systemctl start alpstein-n8n-update-notify.service
journalctl -u alpstein-n8n-update-notify.service -n 50 --no-pager
```

Disable timer:

```bash
sudo systemctl disable --now alpstein-n8n-update-notify.timer
```

---

## 5. Operator commands (script)

```bash
cd /opt/alpstein-ai

# Dry run — prints message when latest > installed; updates last_checked_* only
python3 scripts/ops/n8n_update_notify.py --dry-run

# Dry run with isolated state
python3 scripts/ops/n8n_update_notify.py --dry-run --state-path /tmp/n8n-update-notify/state.json

# One-off live check (loads env manually)
set -a && . /etc/alpstein/n8n-update-notify.env && set +a
python3 scripts/ops/n8n_update_notify.py

# Test message (bypass dedup once; still requires latest > installed)
set -a && . /etc/alpstein/n8n-update-notify.env && set +a
python3 scripts/ops/n8n_update_notify.py --force-notify
```

Unit tests:

```bash
backend/.venv/bin/python -m pytest scripts/ops/test_n8n_update_notify.py -v
```

Check state (no secrets):

```bash
cat /var/lib/alpstein-ops/n8n-update-notify/state.json
```

---

## 6. Verification checklist

| Check | Pass criteria |
|-------|----------------|
| Dry run | Logs `installed`, `latest`, `should_notify=true/false` |
| Dedup | Second run with same latest → no second Telegram |
| New release | When GitHub tag advances → one new Telegram |
| After manual update | Installed tag matches latest → no notify |
| Failure mode | Invalid token → run fails; `last_notified_version` unchanged |
| Timer active | `systemctl list-timers` shows `alpstein-n8n-update-notify.timer` |
| Journal | `journalctl -u alpstein-n8n-update-notify.service` shows exit 0 or logged error |

Record evidence in §7.

---

## 7. Evidence log (operator)

### First production dry-run (systemd / manual)

| Date (UTC) | Method | Installed | Latest | Notified? | journal exit | Notes |
|------------|--------|-----------|--------|-----------|--------------|-------|
| | `dry-run` or `systemctl start` | | | | | |

---

## 8. Rollback

| Action | Steps |
|--------|--------|
| Disable alerts | `sudo systemctl disable --now alpstein-n8n-update-notify.timer` |
| Reset dedup | Edit `last_notified_version` in state.json or delete state file |
| Remove install | `sudo rm /etc/systemd/system/alpstein-n8n-update-notify.{service,timer}` + `daemon-reload` |

No application or database rollback required.

---

## 9. Explicitly forbidden

- `docker compose pull` / `up` / `down -v`
- Workflow import, activation, or credential changes via this tool
- Writes to Alpstein business PostgreSQL
- Use of customer Telegram ingress bot for ops alerts

The systemd unit runs **only** `n8n_update_notify.py` with no post-exec hooks.
