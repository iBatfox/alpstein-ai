# n8n Update Notification Service — Design

**Doc status:** architecture / design only (notification-only)  
**As-of:** 2026-05-29  
**Phase:** Ops — lightweight owner alert  
**Not in scope:** E4 release controller, automatic updates, workflow changes, business PostgreSQL

**Related (boundary):**

- E4 release automation: [`e4-controlled-update-release-automation.md`](e4-controlled-update-release-automation.md) — approval + deploy gates (**future**)
- Manual n8n update: [`../tasks/in-progress/T-ops-n8n-manual-update.md`](../../tasks/in-progress/T-ops-n8n-manual-update.md)
- Owner notifications (MVP product): [`../../specs/flows/notification-flow.md`](../../specs/flows/notification-flow.md) — backend → n8n → Telegram for **leads**; **not** this service

---

## 1. Purpose

Inform the **platform owner** when a **new official n8n release** is published, compared to the **currently running** n8n container image.

| In scope | Out of scope |
|----------|----------------|
| Periodic version check | `docker compose pull` / `up` |
| Telegram text alert | Workflow import/export/activation |
| Dedup per release version | PostgreSQL / business DB writes |
| JSON state on host | E4 `release-ctl` execution |
| Impact summary (heuristic) | Customer ingress paths |

**Goal:** Owner sees one Telegram message per new upstream release. **No update is performed.**

---

## 2. Architecture overview

```text
┌─────────────────────────────────────────────────────────────────┐
│  Host: systemd timer (e.g. daily 09:00 UTC)                      │
│  Unit: alpstein-n8n-update-notify.service (oneshot)             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  scripts/ops/n8n_update_notify.py                                │
│  · read state JSON                                               │
│  · fetch latest release (GitHub API)                             │
│  · read installed version (Docker image tag)                     │
│  · compare semver · build summary · classify impact              │
│  · send Telegram (Bot API) if notify warranted                   │
│  · write state JSON                                              │
└─────┬───────────────────┬───────────────────────┬───────────────┘
      │                   │                       │
      ▼                   ▼                       ▼
 GitHub API          docker inspect           api.telegram.org
 n8n-io/n8n          alpstein_n8n_compose     (owner ops chat)
 releases/latest
```

### Placement decision

| Option | Verdict | Reason |
|--------|---------|--------|
| **Host Python script + systemd timer** | **Recommended** | No backend cron/queue; no n8n business logic; no DB; ops-owned |
| n8n Schedule workflow | Reject | Release/orchestration logic must not live in customer n8n ([E4 §3.2](e4-controlled-update-release-automation.md)) |
| Alpstein backend service | Reject | MVP backend has no job runner; wrong layer for ops polling |
| E4 `release-ctl` | Defer | E4 may **consume** the same state file later; this service does not deploy |

**Container target (portable SoT):** `alpstein_n8n_compose` — image from root [`docker-compose.yml`](../../docker-compose.yml) (e.g. `docker.n8n.io/n8nio/n8n:2.22.5`). Legacy `alpstein_n8n` on host path is out of scope unless operator sets `N8N_UPDATE_NOTIFY_CONTAINER`.

---

## 3. Data flow

```text
1. Timer fires → script starts
2. Load state.json (last_checked_*, last_notified_version)
3. GET GitHub /repos/n8n-io/n8n/releases/latest
      → latest_version, published_at, body (markdown)
4. docker inspect <container> → Image tag → installed_version
5. Normalize both to semver (strip leading "v")
6. Always update: last_checked_at, last_checked_version (= latest)
7. IF NOT should_notify(installed, latest, last_notified):
         → exit 0 (log "no notification")
8. Build summary (≤4 bullets) + impact level from semver/keywords
9. POST Telegram sendMessage (formatted text)
10. IF send OK:
         last_notified_version = latest
         last_notified_at = now
11. Write state.json atomically (write temp + rename)
```

### Notification decision (`should_notify`)

Notify **only if all** are true:

1. `installed_version` parses and `latest_version` parses  
2. `latest_version != installed_version` (semver compare; notify when `latest > installed`)  
3. `latest_version != last_notified_version` (dedup — one alert per upstream release)  
4. Telegram credentials present (otherwise log error, do not advance `last_notified_version`)

**Do not notify when:**

- Installed is already at or ahead of latest (custom tag / hotfix image).  
- Latest was already notified (`last_notified_version == latest_version`).  
- GitHub unreachable (see §7 — do not bump `last_notified_version`).

**Optional operator policy (env):** `N8N_UPDATE_NOTIFY_MIN_SEVERITY=medium` — skip patch-level alerts (default: notify all semver bumps).

---

## 4. Telegram notification service design

### Transport

Direct **[Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)** from the host script — **not** `POST /api/v1/webhook/message` and **not** customer ingress workflows.

| Setting | Purpose |
|---------|---------|
| `N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN` | Ops/release bot token (dedicated or shared with E4 release bot — **not** customer `alpsteinai_0001bot`) |
| `N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID` | Owner DM or ops group (same pattern as `TELEGRAM_CHAT_ID` in ingress docs, separate env name to avoid coupling) |

### Message template (contract)

Plain text (Telegram Markdown optional; keep simple to avoid parse errors):

```text
🚀 n8n Update Available

Version:
{latest_version}

Installed:
{installed_version}

Released:
{release_date_iso}

Changes:

1. {change_1}
2. {change_2}
3. {change_3}
4. {change_4}

Impact Level:
{impact_emoji} {impact_label}

Action:
No update performed.

Decision Required:
Review and approve update if needed.
```

### Summary generation (release notes → 4 bullets)

| Step | Rule |
|------|------|
| Source | GitHub `body` markdown from `/releases/latest` |
| Strip | Remove HTML comments, collapse blank lines |
| Extract | First 4 non-empty lines that look like list items (`-`, `*`, numbered) or sentences under 200 chars |
| Fallback | If fewer than 4 items, pad with `"See full release notes on GitHub."` |
| Truncate | Max 120 chars per bullet; strip markdown links to text |

No LLM required for MVP.

### Impact level (heuristic)

| Condition | Level | Emoji |
|-----------|-------|-------|
| Major semver bump (`x.0.0`) | High | 🔴 |
| Minor bump (`1.x.0`) | Medium | 🟡 |
| Patch bump (`1.2.x`) | Low | 🟢 |
| Body contains `breaking` / `security` (case-insensitive) | Bump one level (cap at High) | — |

Display: `🟢 Low` / `🟡 Medium` / `🔴 High`.

---

## 5. Version tracking strategy

### Installed version (runtime truth)

**Primary:** Docker image tag from running container.

```bash
docker inspect -f '{{.Config.Image}}' "${N8N_UPDATE_NOTIFY_CONTAINER:-alpstein_n8n_compose}"
# → docker.n8n.io/n8nio/n8n:2.22.5  →  installed_version = 2.22.5
```

**Secondary (validation only):** `docker exec … n8n --version` — compare log line to tag; if mismatch, prefer image tag and log warning.

**Compose pin:** Repo [`docker-compose.yml`](../../docker-compose.yml) documents intended tag; runtime inspect is authoritative for “what is running”.

### Latest version (upstream truth)

**Official source:** GitHub Releases API (same artifacts Docker Hub `n8nio/n8n` tags track).

```http
GET https://api.github.com/repos/n8n-io/n8n/releases/latest
Accept: application/vnd.github+json
```

| Field | Use |
|-------|-----|
| `tag_name` | `latest_version` (e.g. `n8n@1.123.4` or `v1.123.4` — normalize) |
| `published_at` | `release_date` in message |
| `body` | Summary input |
| `html_url` | Optional 5th line in Telegram: “Full notes: …” |

**Rate limit:** Unauthenticated 60 req/h — sufficient for daily check. Optional `GITHUB_TOKEN` env for CI/automation headroom (never log token).

**Tag normalization:** Strip `n8n@`, `v` prefix; take semver `MAJOR.MINOR.PATCH` via regex; invalid → abort check with error log (no notify).

### Dedup logic

| State field | Updated when | Purpose |
|-------------|--------------|---------|
| `last_checked_version` | Every successful GitHub fetch | Audit trail |
| `last_checked_at` | Every successful run | Staleness monitoring |
| `last_notified_version` | Only after **successful** Telegram send | Prevent duplicate alerts for same release |
| `last_notified_at` | Same as above | Operator audit |

If owner updates n8n manually to `latest`, next run: `installed == latest` → no notification (even if `last_notified_version` is older).

---

## 6. Storage design

**No Alpstein business PostgreSQL.** No Alembic. No n8n DB writes.

| Store | Path (default) | Contents |
|-------|----------------|----------|
| JSON state file | `/var/lib/alpstein-ops/n8n-update-notify/state.json` | Version + timestamps |
| Log | journald via systemd **or** `/var/log/alpstein/n8n-update-notify.log` | Status lines only — no secrets |

### `state.json` schema

```json
{
  "schema_version": 1,
  "last_checked_at": "2026-05-29T09:00:05Z",
  "last_checked_version": "1.123.4",
  "last_notified_version": "1.123.0",
  "last_notified_at": "2026-05-28T09:00:02Z",
  "last_installed_version": "1.122.0",
  "last_error": null
}
```

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | Migration hook if schema evolves |
| `last_checked_*` | ISO8601 + semver string | Always updated on successful GitHub read |
| `last_notified_*` | ISO8601 + semver string | Only when Telegram succeeds |
| `last_installed_version` | semver string | Snapshot from last run |
| `last_error` | string \| null | Short code/message for operator debug — no stack traces with tokens |

**Atomic write:** `state.json.tmp` → `rename` to `state.json`.

**Permissions:** `root:alpstein-ops` mode `0640`; directory created by install step.

---

## 7. Error handling strategy

| Failure | Behavior | `last_notified_version` |
|---------|----------|---------------------------|
| GitHub timeout / 5xx | Log `GITHUB_UNAVAILABLE`; exit non-zero for systemd visibility | Unchanged |
| GitHub 404 / parse error | Log `GITHUB_PARSE_ERROR`; exit non-zero | Unchanged |
| Docker inspect fails (container down) | Log `CONTAINER_NOT_FOUND`; still fetch latest; **optional** notify-only-upstream mode off by default | Unchanged |
| Invalid semver in tag | Log `VERSION_PARSE_ERROR`; skip notify | Unchanged |
| Telegram 4xx/5xx | Log `TELEGRAM_SEND_FAILED`; exit non-zero | **Unchanged** (retry next schedule) |
| Missing Telegram env | Log `TELEGRAM_NOT_CONFIGURED`; exit 0 | Unchanged |
| State file corrupt | Log `STATE_INVALID`; backup to `.bak`; start fresh state | Unchanged |

**Principles:**

- Never call `docker compose pull|up`.  
- Never mutate n8n workflows or credentials.  
- Fail **closed** on notify: if send uncertain, do not advance `last_notified_version`.  
- Idempotent runs: safe to run timer every hour; dedup prevents spam.

**Retries:** Single attempt per run. systemd `OnFailure=` optional email/webhook later — not MVP.

---

## 8. Implementation plan

### Slice O1 — Design (this document)

- [x] Architecture, data flow, Telegram contract, storage, errors  
- [ ] Human review

### Slice O2 — Script + state (no deploy automation)

| Item | Detail |
|------|--------|
| File | `scripts/ops/n8n_update_notify.py` |
| Tests | `scripts/ops/test_n8n_update_notify.py` (13 unit tests) |
| Deps | stdlib only (`urllib`, `subprocess`, `json`) |
| CLI | `--dry-run` (print message, update `last_checked_*` only) |
| CLI | `--force-notify` (operator test — bypass dedup once) |

### Slice O3 — systemd + ops runbook

| Item | Detail |
|------|--------|
| Units | [`docs/ops/systemd/alpstein-n8n-update-notify.{service,timer}`](../ops/systemd/) → install to `/etc/systemd/system/` |
| Schedule | `OnCalendar=daily`, `RandomizedDelaySec=30min`, `Persistent=true` |
| Env file | `/etc/alpstein/n8n-update-notify.env` (template: `docs/ops/systemd/n8n-update-notify.env.example`) |
| Doc | [`docs/ops/n8n-update-notification-runbook.md`](../ops/n8n-update-notification-runbook.md) |

**Status:** implemented (2026-05-29). Operator must enable timer on host and record first evidence in runbook §7.

### Slice O4 — Verification (operator)

1. `python scripts/ops/n8n_update_notify.py --dry-run`  
2. Temporarily lower `last_notified_version` in state; `--force-notify` → Telegram received  
3. Re-run → no duplicate  
4. Confirm HubSpot n8n (`15678`) untouched  

### E4 handoff (future, optional)

E4 release bot “Update Available” step may **read** the same `state.json` or receive webhook from script — **no code sharing required in O2**.

---

## 9. Security & compliance

- Tokens only in host env file — never in git, workflow JSON, or business DB.  
- Logs: log versions and HTTP status codes — not `bot_token`, not full release body if it contains contributor emails.  
- GitHub API: public repo — no customer PII.  
- Scope: read-only Docker inspect; read-only HTTP GET.

---

## 10. API / product boundary (api-designer)

| Surface | Role |
|---------|------|
| `POST /api/v1/webhook/message` | **Not used** — customer normalized ingress only |
| Telegram Bot API | **Direct** ops notification — outside MVP API envelope |
| Future `GET /api/v1/ops/n8n-release-status` | **Deferred** — not required for notify-only MVP |

No changes to [`specs/api/api-endpoints.md`](../../specs/api/api-endpoints.md) for slice O2.

---

## 11. Rollout recommendation (ops-release-manager)

1. Implement O2–O3 on **staging/personal** host first.  
2. Use **dedicated** ops bot + chat — not customer ingress bot.  
3. Keep timer **disabled** until first successful `--dry-run` reviewed.  
4. Document first production notification in ops runbook § Evidence.  
5. Manual n8n updates remain per [`T-ops-n8n-manual-update.md`](../../tasks/in-progress/T-ops-n8n-manual-update.md) — this service does not replace that runbook.

**Forbidden in all slices:** automatic image pull, compose up, workflow edits, PostgreSQL migrations.
