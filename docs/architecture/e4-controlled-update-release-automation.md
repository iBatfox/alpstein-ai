# E4 — Controlled Update & Release Automation

**Doc status:** spec / architecture (design only)  
**As-of:** 2026-05-28  
**Phase:** E4 — no runtime implementation in this document  
**Canonical runtime:** [`../ops/runtime-map.md`](../ops/runtime-map.md)  
**Deployment contract:** [`../deployment/deployment-contract.md`](../deployment/deployment-contract.md)  
**Task:** [`../../tasks/done/T-e4-controlled-update-release-automation-design.md`](../../tasks/done/T-e4-controlled-update-release-automation-design.md)

---

## 1. Purpose

Define a **central release orchestration layer** so production changes on Contabo never happen through ad-hoc shell sessions alone. Every deployment must be **approved**, **verified**, **tagged**, **logged**, and **reversible**.

This phase does **not** replace human operators for production execution in MVP; it **coordinates and gates** approved operations executed by the controller or operator scripts it invokes.

### Success criteria (mandatory gates)

Production deploy **must not start** unless all are true:

1. Authorized Telegram user approval (staging path + production path)
2. Staging verification **PASS**
3. Backup git tag created and recorded
4. Second production confirmation
5. Immutable audit record written

The system must always answer: **what**, **who**, **when**, **why failed**, and **how to roll back**.

### Out of scope (E4 design)

| Item | Reason |
|------|--------|
| HubSpot n8n (`15678`) | Project boundary |
| AI / prompt / webhook contract changes | Backend / api-designer approval |
| Kubernetes / multi-host orchestration | Post-MVP |
| Automatic production deploy without human confirm | Policy — two-step approval minimum |

---

## 2. System context

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Release Controller (E4.1)                      │
│  state machine · lock · audit · job runner · report generator   │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
    ┌────────▼────────┐              ┌───────▼────────┐
    │ Telegram Bot     │              │ Host executor   │
    │ (E4.2 approval)  │              │ docker compose  │
    └────────┬────────┘              │ git · smoke     │
             │                       └───────┬────────┘
             │                               │
             │         ┌─────────────────────┼─────────────────────┐
             │         │                     │                     │
             │    alpstein_postgres    alpstein_backend    alpstein_n8n_compose
             │         │                     │                     │
             └─────────┴─────────────────────┴─────────────────────┘
                           alpstein_internal
                    workflow: alpstein-customer-ingress
```

**Integration points:**

| Component | Controller interaction |
|-----------|------------------------|
| **Git** | Detect updates; checkout approved SHA; create backup tag |
| **Docker Compose v2** | `docker compose -p alpstein-ai …` only ([`runtime-map.md`](../ops/runtime-map.md)) |
| **Backend** | Readiness `/api/v1/health/ready`; webhook smokes |
| **n8n** | Workflow active check; unified ingress smokes; no workflow JSON edits without promotion slice |
| **Telegram** | Owner bot for approvals (separate from customer ingress bot) |
| **nginx** | Read-only verify upstream `127.0.0.1:15679` — changes require explicit slice |

---

## 3. E4.1 — Release Controller

### 3.1 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Lifecycle | Drive release state machine; reject illegal transitions |
| Locking | One active release per environment (`production`); mutex across controller + executor |
| Execution | Run **approved** step scripts only (allowlist) |
| Coordination | Order: backup tag → staging verify → prod deploy → post-verify |
| Failure handling | Hard stop; optional auto-rollback prep; never continue on red checks |
| Reporting | Structured verification reports for Telegram + audit |

### 3.2 Deployment shape (recommended MVP)

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Host systemd service** (`release-controller`) | Simple on Contabo; direct `docker` socket | Coupled to host | **MVP default** |
| B. Sidecar container on `alpstein_internal` | Isolated | Socket mount, networking | Phase E4-R2 |
| C. n8n workflow | Fast to prototype | Business logic in n8n forbidden by architecture | **Reject** |

**Storage (MVP):** SQLite or JSONL under `/var/lib/alpstein-release/` (outside git) + optional mirror to Postgres later (E4.6). Not the Alpstein business DB — n8n must not write business PostgreSQL.

### 3.3 Release state machine

```text
                    ┌──────────────┐
                    │    IDLE      │
                    └──────┬───────┘
                           │ update detected / operator start
                           ▼
                    ┌──────────────┐
              ┌────│   PENDING    │──── skip staging (policy flag, still audit)
              │    │  APPROVAL    │
              │    └──────┬───────┘
              │           │ [Check Staging] approved
              │           ▼
              │    ┌──────────────┐
              │    │   STAGING    │
              │    │   RUNNING    │
              │    └──────┬───────┘
              │      pass │      fail
              │           ▼           ▼
              │    ┌──────────────┐  ┌──────────────┐
              │    │   STAGING    │  │   STAGING    │
              │    │   PASSED     │  │   FAILED     │──► terminal (no prod)
              │    └──────┬───────┘  └──────────────┘
              │           │ [Deploy Production] + 2nd confirm
              │           ▼
              │    ┌──────────────┐
              │    │ PRODUCTION   │
              │    │  DEPLOYING   │
              │    └──────┬───────┘
              │      ok   │   fail
              │           ▼           ▼
              │    ┌──────────────┐  ┌──────────────┐
              │    │  COMPLETED   │  │ PROD_FAILED  │──► rollback offered
              │    └──────────────┘  └──────┬───────┘
              │                             │
              │                             ▼
              │                      ┌──────────────┐
              └──────────────────────│  ROLLBACK    │
                                     │  RUNNING     │
                                     └──────┬───────┘
                                            ▼
                                     ┌──────────────┐
                                     │ ROLLED_BACK  │
                                     │  or FAILED   │
                                     └──────────────┘
```

| State | Concurrent releases | Production traffic |
|-------|---------------------|--------------------|
| `IDLE` | Allowed (none active) | Normal |
| `STAGING_RUNNING` | **Blocked** | Normal (no prod change) |
| `PRODUCTION_DEPLOYING` | **Blocked** | At risk — deploy window |
| `ROLLBACK_RUNNING` | **Blocked** | Recovery window |

### 3.4 Release lock mechanism

| Lock type | Implementation |
|-----------|----------------|
| **Global release lock** | File lock `/var/lib/alpstein-release/release.lock` or DB row `locks(id=production)` |
| **Compose mutex** | Controller refuses second `docker compose up` while lock held |
| **TTL** | Stale lock recovery after operator timeout (e.g. 2h) with audit entry |

**Forbidden while lock held:** manual `docker compose up`, RECOVERY-style `docker run` n8n, workflow activation changes (except controller job).

### 3.5 Execution flow (approved operations allowlist)

| Step ID | Operation | Preconditions |
|---------|-----------|---------------|
| `git_fetch` | `git fetch origin` | — |
| `git_verify_clean` | `git status --porcelain` empty or documented exception | Staging |
| `git_backup_tag` | `git tag release-backup-YYYYMMDD-HHMM-<shortsha>` | Before prod |
| `compose_config` | `docker compose … config` | Always |
| `compose_up_postgres` | `up -d postgres` | Ordered |
| `compose_up_backend` | `up -d backend` | Postgres healthy |
| `compose_up_n8n` | `up -d n8n` | Backend ready |
| `health_ready` | GET `/api/v1/health/ready` == 200 | After backend |
| `smoke_unified_wc` | POST unified Website Chat webhook | After n8n |
| `smoke_unified_tg` | Telegram inject or live DM checklist | After n8n |
| `n8n_workflow_verify` | Active workflow = `alpstein-customer-ingress` only | Post n8n |

**Executor rule:** Never invoke `docker-compose` (v1) `--force-recreate`. Use `docker compose` v2 per RECOVERY-2.

### 3.6 Failure handling strategy

| Failure class | Controller action | Operator notification |
|---------------|-------------------|------------------------|
| Staging check fail | → `STAGING_FAILED`; **no prod** | Telegram report + audit |
| Migration fail | → `PROD_FAILED`; offer rollback | Immediate |
| Health not 200 | → `PROD_FAILED`; auto-rollback **optional** (policy) | Immediate |
| Smoke fail | → `PROD_FAILED`; recommend rollback | Immediate |
| Lock contention | Reject new release | Telegram “release in progress” |
| Unauthorized Telegram | Ignore callback; audit security event | Admin alert |

---

## 4. E4.2 — Telegram Approval Workflow

### 4.1 UX flow

```text
Update Available (controller → Telegram)
        │
        ▼
┌───────────────────────────────────────┐
│  Release R-20260528-001                │
│  Branch: stabilization/runtime-baseline │
│  Commits: 3 ahead of deployed          │
│  [ Check Staging ]  [ Skip Staging* ]  │
└───────────────────────────────────────┘
        │ Check Staging (authorized only)
        ▼
   (staging pipeline runs)
        │
        ▼
┌───────────────────────────────────────┐
│  Verification Report (PASS / FAIL)    │
│  • git: OK                            │
│  • compose config: OK                 │
│  • health: 200                        │
│  • smoke WC: 200                      │
│  • smoke TG: pending live DM          │
│  [ Deploy Production ]  [ Cancel ]    │
└───────────────────────────────────────┘
        │ Deploy Production
        ▼
┌───────────────────────────────────────┐
│  Confirm: type DEPLOY or 2nd button   │
│  [ Confirm Deploy ]  [ Abort ]        │
└───────────────────────────────────────┘
```

\*`Skip Staging` disabled by default in production policy; requires separate admin role if ever enabled.

### 4.2 Security model

| Control | Requirement |
|---------|-------------|
| **User allowlist** | `RELEASE_APPROVER_TELEGRAM_USER_IDS` (comma-separated integers) |
| **Callback validation** | HMAC-signed payload: `release_id + action + exp` |
| **Token expiry** | Default 15 minutes per approval step; single-use nonce |
| **Replay protection** | Store consumed `callback_nonce` in audit DB |
| **Bot separation** | **Owner / release bot** (`AlpsteinAIbot` or dedicated) — not customer `alpsteinai_0001bot` |
| **Unauthorized** | Silent drop + `SECURITY_DENIED` audit row; no state transition |

### 4.3 Callback actions (enum)

| Action | Maps to state transition |
|--------|--------------------------|
| `staging_start` | `PENDING_APPROVAL` → `STAGING_RUNNING` |
| `staging_skip` | Policy-gated → `STAGING_PASSED` (audit flag) |
| `cancel` | → `IDLE` |
| `prod_deploy_request` | `STAGING_PASSED` → await confirm |
| `prod_deploy_confirm` | → `PRODUCTION_DEPLOYING` |
| `rollback_request` | `PROD_FAILED` → `ROLLBACK_RUNNING` |

### 4.4 Action confirmation logging

Every callback logs: `release_id`, `telegram_user_id`, `action`, `timestamp_utc`, `nonce`, `result` (accepted/denied/expired).

---

## 5. E4.3 — Staging Verification

### 5.1 Pipeline stages (hard stop on first failure)

| # | Check | Method | Fail code |
|---|-------|--------|-----------|
| 1 | Git repo health | `git rev-parse`, `git fsck` (optional), remote reachable | `GIT_UNREACHABLE` |
| 2 | Branch validation | Target branch matches policy; SHA exists | `BRANCH_POLICY` |
| 3 | Working tree | Clean or explicit `ALLOW_DIRTY_RELEASE` | `GIT_DIRTY` |
| 4 | Backup tag | Create `release-backup-*` before any container change | `TAG_FAILED` |
| 5 | Compose config | `docker compose … config` exit 0 | `COMPOSE_CONFIG` |
| 6 | Env keys present | `POSTGRES_PASSWORD`, `N8N_BACKEND_API_TOKEN`, etc. (names only) | `ENV_MISSING` |
| 7 | Docker images | Build or pull `alpstein-ai-backend:local` if Dockerfile changed | `IMAGE_BUILD` |
| 8 | Migration dry-run | `alembic current` + `alembic heads` compare; optional `upgrade --sql` in staging | `MIGRATION_DRIFT` |
| 9 | Postgres healthy | `pg_isready` via compose | `DB_NOT_READY` |
| 10 | Backend readiness | `/api/v1/health/ready` == 200 | `BACKEND_NOT_READY` |
| 11 | n8n → backend | `wget http://backend:8000/api/v1/health/ready` from n8n container | `N8N_BACKEND_UNREACHABLE` |
| 12 | Unified WC smoke | POST unified Website Chat path | `SMOKE_WC_FAIL` |
| 13 | Unified TG smoke | Webhook inject + operator live DM checklist | `SMOKE_TG_FAIL` |
| 14 | Legacy port scan | No listeners on `8010`, `15432`, public `8088`/`8090` | `SURFACE_UNSAFE` |
| 15 | Single n8n owner | Only `alpstein_n8n_compose` on `15679` | `N8N_DUPLICATE` |

**Staging on single host (MVP):** Verification runs against **candidate SHA** using controlled recreate via `docker compose` v2 without switching nginx. Optional future: `docker compose -f docker-compose.staging.yml` on alternate ports.

### 5.2 Verification report schema (JSON)

```json
{
  "release_id": "R-20260528-001",
  "phase": "staging",
  "verdict": "PASS",
  "git_sha": "abc1234",
  "backup_tag": "release-backup-20260528-1200-abc1234",
  "checks": [
    {"id": "health_ready", "status": "pass", "duration_ms": 120}
  ],
  "generated_at": "2026-05-28T12:00:00Z"
}
```

### 5.3 Failure matrix (excerpt)

| Code | Prod deploy allowed? | Rollback tag used? |
|------|----------------------|--------------------|
| `STAGING_FAILED` | **No** | N/A |
| `SMOKE_WC_FAIL` | **No** | N/A |
| `MIGRATION_DRIFT` | **No** | N/A |
| `SURFACE_UNSAFE` | **No** (warn) | N/A |

---

## 6. E4.4 — Production Deployment Gate

### 6.1 Separate approval

| Gate | Approver | Evidence |
|------|----------|----------|
| Staging | First `[Check Staging]` | Staging report `PASS` |
| Production | `[Deploy Production]` + `[Confirm Deploy]` | Distinct callback nonces |

Minimum **two distinct Telegram interactions** for production.

### 6.2 Deployment lock during prod

- Acquire global lock before first `compose up` mutation.
- Record `deploy_started_at`, `git_sha`, `backup_tag`.
- Execute allowlisted steps in [`runtime-map.md`](../ops/runtime-map.md) order.
- **Do not** deactivate `alpstein-customer-ingress` unless workflow promotion is in scope.

### 6.3 Safe deployment procedure (production slice)

```bash
# Executed by controller only — illustrative
cd /opt/alpstein-ai
set -a && . ./.env && set +a
export N8N_HOST_PORT=15679 POSTGRES_HOST_PORT=15433 BACKEND_HOST_PORT=8000 LANGFUSE_TRACING_ENABLED=false

docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend n8n
# post-deploy verification (same as staging subset)
```

### 6.4 Post-deployment verification checklist

- [ ] `alpstein_backend` healthy; readiness **200**
- [ ] `alpstein_n8n_compose` → backend **200**
- [ ] Unified Website Chat smoke **200**
- [ ] Telegram live DM or approved inject smoke
- [ ] `alpstein-customer-ingress` active; archived workflows inactive
- [ ] HubSpot n8n untouched
- [ ] Audit `COMPLETED` with report attachment

---

## 7. E4.5 — Rollback Automation

### 7.1 Rollback preparation (every release)

| Artifact | Purpose |
|----------|---------|
| `release-backup-YYYYMMDD-HHMM-<sha>` git tag | Code rollback point |
| `n8n/workflows/backups/<release_id>/` scrubbed export | Workflow rollback |
| `runtime-snapshot.json` (names only) | Env var names, workflow IDs, image digests |
| Compose container IDs | Record before deploy |

### 7.2 Rollback triggers

| Trigger | Auto-initiate? |
|---------|----------------|
| Failed health after prod | Policy: suggest; operator confirm |
| Failed migration | **Block**; suggest rollback |
| Runtime instability (repeated 503) | Suggest |
| Manual operator Telegram `[Rollback]` | Yes |
| Failed staging | No prod deploy — no rollback needed |

### 7.3 Rollback execution workflow

```text
1. Acquire lock (ROLLBACK_RUNNING)
2. git checkout <backup_tag>  (or recorded SHA)
3. docker compose up -d postgres backend n8n  (v2)
4. Re-import n8n backup if workflow changed
5. Verify health + smokes
6. State → ROLLED_BACK
7. Audit + Telegram summary
```

**Forbidden:** `docker volume rm`, `alembic downgrade` without migration-engineer plan.

### 7.4 Failure-response matrix

| Symptom | First action | Verify |
|---------|--------------|--------|
| Backend 503 DATABASE | Postgres up on `alpstein_internal` | [`recovery-runtime-source-of-truth`](../audits/recovery-runtime-source-of-truth-2026-05-28.md) |
| ContainerConfig error | Ensure `docker compose` v2, not v1 recreate | RECOVERY-2 |
| n8n timeout to backend | `BACKEND_BASE_URL=http://backend:8000` | runtime-map |
| Wrong workflow active | Restore E1.9 backup export | E1.9 audit |

---

## 8. E4.6 — Audit & Release History

### 8.1 Audit schema (logical)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Immutable row |
| `release_id` | string | Human-readable `R-YYYYMMDD-NNN` |
| `event_type` | enum | `STATE_CHANGE`, `APPROVAL`, `CHECK`, `DEPLOY`, `ROLLBACK`, `SECURITY` |
| `actor_type` | enum | `telegram_user`, `controller`, `operator_shell` |
| `actor_id` | string | Telegram user id or `system` |
| `from_state` | string | nullable |
| `to_state` | string | nullable |
| `action` | string | e.g. `prod_deploy_confirm` |
| `result` | enum | `success`, `failure`, `denied` |
| `metadata_json` | JSON | Check IDs, durations, no secrets |
| `created_at` | UTC timestamp | Append-only |

**Immutability:** append-only store; corrections via compensating `CORRECTION` event, never UPDATE/DELETE.

### 8.2 Release timeline API (future)

| Query | Use |
|-------|-----|
| `GET /releases?limit=20` | Operator dashboard |
| `GET /releases/{id}` | Full timeline + reports |
| `GET /releases/{id}/audit` | Compliance export |

MVP: CLI `release-ctl history` reading SQLite.

### 8.3 Operational reporting

| Report | Audience |
|--------|----------|
| Staging summary | Telegram markdown |
| Prod completion | Telegram + audit |
| Weekly release digest | Operator |

**Never log:** tokens, `.env` values, message bodies, webhook secrets.

---

## 9. Implementation phases (recommended)

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| **E4-R0** | This spec + runbook skeleton | — |
| **E4-R1** | `release-ctl` CLI + state machine + audit SQLite | E4-R0 |
| **E4-R2** | Telegram bot + callbacks | E4-R1 |
| **E4-R3** | Staging pipeline scripts | E4-R1 |
| **E4-R4** | Prod gate + compose executor | E4-R3 |
| **E4-R5** | Rollback automation | E4-R4 |

**No E4-R* work starts without reviewer sign-off on this document.**

---

## 10. Open questions

| # | Question | Default proposal |
|---|----------|------------------|
| Q1 | Dedicated release bot vs reuse `AlpsteinAIbot`? | Dedicated `@AlpsteinReleaseBot` |
| Q2 | Staging on same host vs second compose project? | Same host; verify-before-swap MVP |
| Q3 | Auto-rollback on health fail? | Off; operator confirm |
| Q4 | Who may `Skip Staging`? | Nobody in prod |
| Q5 | Controller code location | `ops/release-controller/` in repo |
| Q6 | Update detection | Manual `/release check` + optional cron |

---

## 11. Related documents

| Doc | Role |
|-----|------|
| [`../ops/e4-release-controller-runbook.md`](../ops/e4-release-controller-runbook.md) | Operator procedures (when implemented) |
| [`../ops/n8n-unified-customer-ingress-runbook.md`](../ops/n8n-unified-customer-ingress-runbook.md) | Smoke targets |
| [`../ops/runtime-map.md`](../ops/runtime-map.md) | Allowed compose commands |
| [`../audits/e1-9-unified-ingress-cutover-2026-05-28.md`](../audits/e1-9-unified-ingress-cutover-2026-05-28.md) | Rollback workflow backups |
