# n8n runtime / export parity (Phase C — Step C1)

**Doc status:** canonical (ops governance)  
**As-of:** 2026-05-27  
**Phase:** C1 — audit and policy only (no workflow redesign, no live cutover)  
**Prerequisites:** Phase B complete (B2.9 clean-clone gate passed)

**Related:** [`n8n/workflows/README.md`](../../n8n/workflows/README.md), [`runtime-registry.md`](../../n8n/workflows/runtime-registry.md), [`deployment-contract.md`](../deployment/deployment-contract.md) §11 RDU/RBU, [`clean-clone-gate-2026-05-27.md`](../audits/clean-clone-gate-2026-05-27.md)

---

## 1. Executive summary

| Finding | Severity |
|---------|----------|
| Canonical exports exist for T13 test + T14 Telegram paths with `versionId` stamps | OK |
| Repo exports intentionally use `"active": false` — activation is runtime-only | **By design** — drift risk if registry stale |
| Contabo runtime has **multiple** imported copies of the same Telegram workflow | **High** — silent wrong-workflow activation |
| Export scrub gate G-EXP-2 | **Automated** — [`scripts/n8n/export-scrub.sh`](../../scripts/n8n/export-scrub.sh) |
| `My_workflow.json` quarantined via `.gitignore` | OK |
| Portable clone path does not import workflows (B2.9) | OK for infra gate; **G5 webhook** still manual |

**C1 outcome:** Parity **discipline defined**; full **enforcement** is Phase C implementation (C2–C4), not this step.

---

## 2. Current export strategy (audit)

### What is tracked in git

| Artifact | Role |
|----------|------|
| `t13_workflow1_test_webhook_skeleton.json` | Canonical test webhook + owner notify (T13.5 topology) |
| `t14_workflow_telegram_customer_ingress_skeleton.json` | Canonical Telegram customer ingress (T14 + OC-3 + Alpstein greeting) |
| `backups/alpstein-incoming-message-test_gate2_2026-05-25.json` | Dated rollback snapshot (Gate 2) |
| `n8n/.env.example` | Env names only; portable `BACKEND_BASE_URL=http://backend:8000` |
| Ops runbooks | Execution evidence, runtime IDs, import notes |

### What is intentionally not in git

| Artifact | Storage |
|----------|---------|
| `n8n/.env`, tokens, `TELEGRAM_CHAT_ID` | Host / compose env (gitignored) |
| Telegram bot tokens | n8n encrypted credential store (`alpstein_n8n_data` volume) |
| Runtime workflow UUIDs | n8n SQLite — documented in [`runtime-registry.md`](../../n8n/workflows/runtime-registry.md) |
| Ad-hoc UI exports | `My_workflow.json` (gitignored) |

### Export conventions in use

| Field | Policy |
|-------|--------|
| `"active": false` | Default in repo; prevents accidental activation on import |
| `versionId` | Human stamp (`t13-5-owner-notify-v5`, `t14-alpstein-ai-greeting-v1`) — bump on every reviewed change |
| `credentials.telegramApi` | **Name only** (e.g. `alpsteinai_0001bot`, `AlpsteinAIbot`) — re-bind after import |
| HTTP to backend | `$env.BACKEND_BASE_URL` + `$env.N8N_BACKEND_API_TOKEN` — never literals |
| Node `id` / `webhookId` | Stable in export for topology; OK to keep if unchanged |

---

## 3. Runtime vs export parity risks

| ID | Drift vector | Impact | Mitigation (C1 policy) |
|----|--------------|--------|-------------------------|
| D1 | UI edit without export to git | Runtime diverges from reviewed code | Freeze: export → review → commit → bump `versionId` |
| D2 | Import creates **new** workflow ID; old copy left **active** | Telegram 403 / duplicate triggers | Deactivate all same-name workflows; single active; update registry |
| D3 | Stale `runtime-registry.md` | Wrong rollback target | Registry update mandatory in same change set as activate |
| D4 | Credential bound by ID from another host | Import succeeds, send fails | Name-only in git; re-bind in UI after every import |
| D5 | `BACKEND_BASE_URL` profile mismatch (legacy `8010` vs `backend:8000`) | 200 health elsewhere, webhook failures | Env profile documented per deployment; compose override on portable |
| D6 | `N8N_ENCRYPTION_KEY` change without volume backup | Credential loss | Key rotation runbook; no key change in parity tasks |
| D7 | Telegram webhook secret desync after activate without restart | 403 at trigger, no execution | deactivate → restart n8n → activate → restart |
| D8 | Backup JSON mistaken for canonical | Wrong topology deployed | `backups/` not import target unless rollback doc names file |
| D9 | `versionId` not bumped | Cannot prove which export ran | Required on any node/expression change |
| D10 | Execution-only “fixes” in production UI | Unreviewable behavior | Treat as incident; export or revert |

---

## 4. Recommended repository structure

**Keep flat `n8n/workflows/`** with README + registry (no new tooling in C1).

```text
n8n/
  .env.example
  docker-compose.yml          # LEGACY Contabo only
  workflows/
    README.md
    runtime-registry.md
    t13_workflow1_test_webhook_skeleton.json
    t14_workflow_telegram_customer_ingress_skeleton.json
    backups/                  # YYYY-MM-DD gate snapshots only
  scripts/                    # credential verify/import helpers (no secrets)
```

**Do not** add per-environment workflow copies in git — use `versionId` + registry row instead.

**C2 (done):** [`scripts/n8n/export-scrub.sh`](../../scripts/n8n/export-scrub.sh) — check (default) or `--scrub` normalize in place.

---

## 5. Export governance rules

### E1 — Source of truth

1. **Git canonical export** defines allowed nodes, connections, and expressions.
2. **Runtime** is a deployment of a specific `(git commit, versionId, registry workflow ID)`.
3. If runtime behavior differs from export, **runtime is wrong** until export is updated or runtime re-imported.

### E2 — Change control

| Step | Required |
|------|----------|
| Edit in n8n UI (if unavoidable) | Same session: Export JSON |
| Scrub secrets / verify no credential `id` | Manual checklist (C2 automates) |
| Bump `versionId` in export | Yes |
| Update ops doc if topology/flags change | Yes |
| Update `runtime-registry.md` if import/activate | Yes |
| Human review before commit | Yes — no agent commit unless asked |

### E3 — Credentials

| Rule | Detail |
|------|--------|
| In git | Credential **name** references only |
| Never in git | Bot token, `accessToken`, chat IDs, API token literals |
| After import | Operator re-binds each `telegramApi` / Header Auth in UI |
| Owner vs customer | `AlpsteinAIbot` + `TELEGRAM_CHAT_ID` vs `alpsteinai_0001bot` + `telegram_chat_id` — see dual-bot doc |

### E4 — Activation

| Environment | Policy |
|-------------|--------|
| Repo export | `"active": false` always |
| Contabo live | Activation only via named ops task; one Telegram trigger per bot |
| Portable compose / clean clone | No activate in automated gate until C4 deploy checklist |

### E5 — Backups

- `backups/*.json` = **RBU snapshots**, not day-to-day source of truth.
- Filename must include workflow purpose + date + gate id.
- Same scrub rules as canonical exports before commit.

---

## 6. Runtime verification procedure

Run after import and before activation (or after activation for smoke).

### R1 — Export identity

```bash
# From repo root — expect false + known versionId
grep -E '"active"|"versionId"' n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json
```

### R2 — Single active path (Telegram)

```bash
# Inside n8n DB or UI: count active workflows named alpstein-incoming-message-telegram
# EXPECT: 0 before controlled activate, 1 after
```

### R3 — Backend reachability (profile-correct URL)

```bash
# Portable
docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
# Legacy (when using alpstein_n8n container)
docker exec alpstein_n8n wget -qO- http://172.20.0.1:8010/api/v1/health
```

### R4 — Webhook auth (Telegram ingress)

- nginx or n8n log: Telegram IP → POST webhook → **200** (not 403 `Provided secret is not valid`).
- New execution appears in n8n for real DM.

### R5 — Node-level smoke (optional)

| Node | Check |
|------|--------|
| Normalize | Drops non-private / non-text |
| POST Backend | `success: true`; no secrets in execution log |
| Shape reply | `reply_to_customer` present |
| Telegram Send | `ok: true`; customer credential only |
| Owner notify | Runs only when `notify_owner`; owner credential + `TELEGRAM_CHAT_ID` |

### R6 — Parity sign-off

| Field | Value |
|-------|--------|
| Git commit | |
| Export `versionId` | |
| Runtime workflow ID | |
| Environment | Contabo legacy / portable |
| Execution IDs (smoke) | |

---

## 7. Safe export / import operational flow

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Deactivate workflow(s) with same name / same Telegram bot │
│ 2. Export from UI OR promote reviewed JSON from git          │
│ 3. Scrub + bump versionId + commit (if topology changed)     │
│ 4. import:workflow into target n8n instance                  │
│ 5. Re-bind credentials (names in export)                     │
│ 6. Verify R3–R4 (no activate yet)                            │
│ 7. Activate ONE workflow → restart n8n (Telegram paths)      │
│ 8. Update runtime-registry.md + ops doc execution table      │
│ 9. Smoke test (Gate 1 or T14 matrix)                         │
└─────────────────────────────────────────────────────────────┘
```

**Portable import** must not use live Contabo volume unless cutover approved.

**Never** `import:workflow` + `active` on production during C-phase without explicit operator task.

---

## 8. Rollback-safe workflow procedure (RBU)

Atomic unit for n8n rollback:

```text
RBU-n8n = git tag/commit
        + canonical export filename + versionId
        + runtime-registry workflow ID (pre-rollback)
        + optional backups/ snapshot filename
        + credential re-bind checklist (names only)
```

| Action | Steps |
|--------|--------|
| **Rollback topology** | Deactivate current → import previous export from `backups/` or git tag → re-bind creds → restart → activate → smoke |
| **Rollback activation only** | Deactivate bad ID; activate known-good ID from registry |
| **Emergency stop** | Deactivate all `alpstein-incoming-message-*`; clear Telegram webhook via BotFather or deactivate trigger |

Rollback does **not** restore n8n execution history or PostgreSQL message data.

---

## 9. Verification gates before deploy

| Gate | Pass criteria | Blocks |
|------|---------------|--------|
| **G-EXP-1** | Canonical file exists; `versionId` bumped if changed | Deploy without reviewed export |
| **G-EXP-2** | `scripts/n8n/export-scrub.sh` exit 0 — JSON valid, `active: false`, `versionId`, name-only credentials, no secrets / forbidden runtime fields | Commit / import |
| **G-EXP-3** | `runtime-registry.md` matches target host IDs | Activation |
| **G-EXP-4** | Exactly one active Telegram customer workflow per bot | Telegram cutover |
| **G-EXP-5** | `BACKEND_BASE_URL` matches deployment profile | End-to-end |
| **G-EXP-6** | Readiness 200 from n8n container | Workflow test |
| **G-EXP-7** | T13 Gate 1 or T14 matrix executions recorded | Production sign-off |

**B2.9 G6** (n8n → backend network) is necessary but **not sufficient** for workflow parity.

---

## 10. Minimal operational policy (n8n changes)

1. **No silent UI edits** on Contabo live workflows — export and reconcile or revert.
2. **One active** workflow per Telegram bot credential.
3. **Repo `active: false`** — activation is a documented operator action.
4. **Deterministic restarts** after Telegram workflow activate/deactivate.
5. **No** workflow changes bundled with backend feature releases unless `versionId` and registry updated in same RDU.
6. **Portable path** uses `http://backend:8000`; **legacy** uses `http://172.20.0.1:8010` — never mix on one instance.
7. **HubSpot** `integrationhubspot_n8n` — out of scope; do not share volumes or compose projects.

---

## 11. Suggested implementation task breakdown (Phase C)

| Task | Scope | Delivers |
|------|--------|----------|
| **C1** (this doc) | Audit + policy + registry | **Done** |
| **C2 / T14.6** | **done** — export scrub + G-EXP-2 | [`scripts/n8n/export-scrub.sh`](../../scripts/n8n/export-scrub.sh) |
| **C3** | Parity diff tool | Compare runtime workflow JSON hash vs canonical export (node names, connections) |
| **C4** | Pre-deploy checklist automation | Script: registry + active count + health + optional dry-run webhook |
| **C5 / T14.5** | Telegram regression gate | Owner notify + duplicate matrix on canonical export |
| **C6** | Clean-clone G5 extension | Documented import + Gate 1 smoke in portable gate transcript |
| **C7** | T13.8 (optional) | Scheduled export backup to `backups/` with scrub |

**Out of scope:** Kubernetes, observability, AI changes, new workflow features, microservices.

---

## 12. Spec / contract impact

| Document | Change needed |
|----------|----------------|
| `specs/api/webhooks.md` | None — contract unchanged |
| `specs/architecture/n8n-architecture.md` | Optional pointer to this policy (handoff api-designer / architect) |
| `deployment-contract.md` RDU §11 | Already requires canonical exports — link this doc in §14 |

---

## 13. Rollback note (C1)

Reverting C1 is **docs-only**: delete or revert `docs/ops/n8n-runtime-export-parity.md`, `n8n/workflows/README.md`, `runtime-registry.md`, task record. **No** runtime impact.

---

## 14. Remaining drift before C2 / B2.8+

| Item | Owner |
|------|--------|
| T14.6 scrub automation | **done** (C2) |
| T14.5 regression on canonical Telegram export | C5 |
| Portable clean-clone G5 webhook with import | C6 |
| Stale duplicate Telegram workflow rows on Contabo | Operator cleanup |
| `runtime-reproducibility-audit.md` (2026-05-27) | Superseded for n8n by this doc where they conflict |

---

---

## 15. G-EXP-2 gate (C2 / T14.6)

**Command (from repo root, clean clone):**

```bash
scripts/n8n/export-scrub.sh
```

**Pass:** exit `0`, message `G-EXP-2: PASS`.

**Normalize before commit (optional):**

```bash
scripts/n8n/export-scrub.sh --scrub
git diff n8n/workflows/
```

**Checks:**

| Check | Policy |
|-------|--------|
| Canonical files only | `t13_*`, `t14_*` at `n8n/workflows/`; `backups/*.json` hygiene only |
| `My_workflow.json` | Must not be git-tracked; local gitignored copy warns only |
| `active` | `false` |
| `versionId` | Non-empty string stamp |
| Credentials | `name` only — no `id`, no `accessToken` |
| Forbidden root keys | No `pinData`, `shared`, `staticData`; no workflow-level `id` |
| Secrets | Regex scan for token literals (Telegram bot shape, Bearer, `sk-`, etc.) |

**Verified:** 2026-05-27 on canonical exports (3 files) in worktree.

**RBU drill note (2026-05-27):** At git tag `baseline-c2-export-scrub-gate` (`02a4ee8`), the script is **not** in the repository — only uncommitted worktree copy exists. See [`disposable-rbu-drill-2026-05-27.md`](../audits/disposable-rbu-drill-2026-05-27.md).

---

*End of n8n runtime/export parity doc.*
