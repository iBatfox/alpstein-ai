# E4 — Release Controller — Operations Runbook (skeleton)

**Doc status:** spec / pre-implementation  
**As-of:** 2026-05-28  
**Architecture:** [`../architecture/e4-controlled-update-release-automation.md`](../architecture/e4-controlled-update-release-automation.md)  
**Runtime map:** [`runtime-map.md`](runtime-map.md)

> **Not live yet.** This runbook defines operator expectations once `release-ctl` / Telegram approval is implemented. Until then, follow manual RECOVERY / E1.9 procedures.

---

## 1. When to use

| Scenario | Tool |
|----------|------|
| Planned deploy after merge to `stabilization/runtime-baseline` | Release Controller (future) |
| Emergency recovery | [`recovery-runtime-source-of-truth-2026-05-28.md`](../audits/recovery-runtime-source-of-truth-2026-05-28.md) manual path |
| Workflow-only promotion | [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md) |

---

## 2. Preconditions (all releases)

- [ ] Task or approved hotfix documented
- [ ] `recovery-runtime-stable-*` or newer baseline tag understood
- [ ] Root `.env` has `POSTGRES_*`, `N8N_BACKEND_API_TOKEN` (values not logged)
- [ ] `docker compose` v2 available (`docker compose version`)
- [ ] HubSpot n8n **15678** untouched
- [ ] No other release lock active

---

## 3. Manual fallback (current production)

Until E4 is implemented, use this ordered checklist:

### 3.1 Pre-deploy

```bash
cd /opt/alpstein-ai
git status -sb
git log -3 --oneline
git tag "release-backup-$(date -u +%Y%m%d-%H%M)-$(git rev-parse --short HEAD)"
set -a && . ./.env && set +a
export N8N_HOST_PORT=15679 POSTGRES_HOST_PORT=15433 BACKEND_HOST_PORT=8000 LANGFUSE_TRACING_ENABLED=false
docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config
```

### 3.2 Deploy

```bash
docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend n8n
```

**Forbidden:** `docker-compose --force-recreate` (v1).

### 3.3 Verify

```bash
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health/ready',timeout=10).status_code)"
docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
# Website Chat + Telegram smokes — see n8n-unified-customer-ingress-runbook.md
```

---

## 4. Telegram approval (future)

| Step | Operator action |
|------|-----------------|
| 1 | Receive “Update Available” on release bot |
| 2 | Tap **Check Staging** (authorized user_id only) |
| 3 | Review verification report — must be **PASS** |
| 4 | Tap **Deploy Production** then **Confirm Deploy** |
| 5 | Confirm post-deploy Telegram summary |

Unauthorized callbacks are ignored and audited.

---

## 5. Rollback (future + current)

| Trigger | Action |
|---------|--------|
| Failed smoke / health | Stop; do not retry prod deploy |
| Rollback approved | `git checkout <backup_tag>` + compose up + n8n backup restore per E1.9 |
| Unified ingress broken | Deactivate unified; restore archived workflows from `n8n/workflows/backups/e1-9-cutover-2026-05-28/` |

Record: release_id, backup_tag, execution evidence in ops audit doc.

---

## 6. Environment variables (names only)

| Variable | Purpose |
|----------|---------|
| `RELEASE_APPROVER_TELEGRAM_USER_IDS` | Allowlist |
| `RELEASE_BOT_TOKEN` | Telegram Bot API (secret) |
| `RELEASE_CALLBACK_HMAC_SECRET` | Sign callbacks |
| `RELEASE_LOCK_PATH` | File lock location |
| `RELEASE_AUDIT_DB_PATH` | SQLite path |

Plus existing: `POSTGRES_*`, `N8N_BACKEND_API_TOKEN`, `N8N_HOST_PORT`, `LANGFUSE_TRACING_ENABLED`.

---

## 7. Evidence recording

After any manual or controller release, update:

- Relevant `docs/ops/*.md` section with date + pass/fail
- `docs/project-status/current-state.md` if baseline changed
- n8n execution IDs for smokes (not message bodies)

---

## 8. Related

| Doc | Topic |
|-----|--------|
| [`operational-ingress-policy.md`](operational-ingress-policy.md) | Single backend URL |
| [`runtime-surface-hardening.md`](runtime-surface-hardening.md) | Port safety |
| [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md) | Compose v2 |
