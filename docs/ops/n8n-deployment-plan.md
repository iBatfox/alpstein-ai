**Doc status:** deprecated  
**Tier:** ops/archived (pending move)

# n8n Deployment Plan (T13.0 — design only)

**Status:** T13.0-impl **implementation committed** (compose + runtime docs) — **runtime not started**; waiting for operator review and `docker-compose up`  
**Date:** 2026-05-25  
**CLI:** This server uses **docker-compose v1.29** — commands use `docker-compose` (hyphen), not `docker compose`.  
**Purpose:** Project-local n8n for Alpstein AI T13 workflows, isolated from existing HubSpot n8n.

**Related:** [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) · [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) · [`specs/architecture/deployment.md`](../../specs/architecture/deployment.md) · [`specs/architecture/n8n-architecture.md`](../../specs/architecture/n8n-architecture.md)

---

## 1. Why T13.0 is needed

T13.1–T13.3 workflow JSON exists in repo, but **Gate 1 runtime verification** requires a running n8n instance with env vars (`BACKEND_BASE_URL`, `N8N_BACKEND_API_TOKEN`) and persistent credentials storage.

This server already runs **`integrationhubspot_n8n`** (HubSpot integration — **do not modify**). Alpstein needs a **separate** n8n container, volume, port, and compose project.

**Observed on server (2026-05-25):**

| Service | Container | Host bind | Notes |
|---------|-----------|-----------|--------|
| HubSpot n8n | `integrationhubspot_n8n` | `127.0.0.1:15678→5678` | Leave unchanged |
| Alpstein Postgres | `backend_postgres` | `127.0.0.1:15432→5432` | Backend DB |
| Alpstein backend | host `uvicorn` | `127.0.0.1:8000` | Not containerized yet |

Alpstein n8n must use a **different host port** than `15678`.

---

## 2. Recommended layout (repo)

Align with [`deployment.md`](../../specs/architecture/deployment.md) §5 while keeping n8n self-contained:

```text
/opt/alpstein-ai/
├── n8n/
│   ├── .env                 # runtime secrets (gitignored) — canonical path
│   ├── .env.example         # placeholder names only (committed)
│   ├── docker-compose.yml   # Alpstein n8n only (T13.0-impl)
│   └── workflows/           # git-tracked workflow exports (import source)
│       └── t13_workflow1_test_webhook_skeleton.json
├── backend/
├── docker/                  # reserved for future full-stack compose
├── infrastructure/          # reserved for shared infra
└── docs/ops/
    └── n8n-deployment-plan.md
```

**Decision:** compose file lives at **`/opt/alpstein-ai/n8n/docker-compose.yml`**, not repo root, because:

- env file path is fixed at **`/opt/alpstein-ai/n8n/.env`** (per project requirement);
- isolates Alpstein n8n lifecycle from `integrationhubspot_n8n` and future root `docker-compose.yml`;
- `n8n/workflows/` stays co-located with the service that consumes imports.

Root `docker-compose.yml` (nginx + backend + postgres + n8n) remains a **future** production milestone per deployment spec.

---

## 3. Container identity

| Setting | Value | Rationale |
|---------|--------|-----------|
| Container name | `alpstein_n8n` | Explicit; no collision with `integrationhubspot_n8n` |
| Compose project name | `alpstein-n8n` | `docker-compose -p alpstein-n8n` isolates resources |
| Image | `docker.n8n.io/n8nio/n8n` (pinned tag in impl) | Official image |
| Internal port | `5678` | n8n default per architecture spec |
| Host bind | `127.0.0.1:15679:5678` | Next free local port after HubSpot `15678`; **localhost only** for MVP dev |

**Do not** map `5678` on host — conflicts with spec default and other services.

Future production: expose via nginx at `n8n.alpstein-ai.ch` (HTTPS + basic auth or SSO), not wide-open host port.

---

## 4. Port strategy

```text
Host (127.0.0.1)          Container (alpstein_n8n)
─────────────────         ────────────────────────
15679 ──────────────────► 5678   (n8n UI + webhooks)

integrationhubspot_n8n:
15678 ──────────────────► 5678   (unchanged — separate container)
```

| Access | URL pattern (dev) |
|--------|-------------------|
| n8n UI | `http://127.0.0.1:15679` |
| Test webhook | `http://127.0.0.1:15679/webhook-test/alpstein/test/incoming` |
| Production webhook (after activate) | `http://127.0.0.1:15679/webhook/alpstein/test/incoming` |

SSH tunnel or nginx required for remote admin — do not bind `0.0.0.0` without auth + TLS in production.

---

## 5. Volume strategy

| Volume | Mount | Purpose |
|--------|-------|---------|
| Named volume `alpstein_n8n_data` | `/home/node/.n8n` | **Required** — workflows, credentials, SQLite, encryption state (per `n8n-architecture.md` §11) |

**Do not** bind-mount `n8n/workflows/` into `/home/node/.n8n` for MVP:

- n8n persists workflows in its internal store after import;
- repo `n8n/workflows/` is **version control + review** (T13.8 export hygiene);
- import flow: commit JSON → import via n8n UI/CLI → activate in n8n DB on volume.

**Do not** share volumes with `integrationhubspot_n8n`.

Backup: include `alpstein_n8n_data` in ops backup plan (future); document volume name in implementation task.

---

## 6. Environment file

**Path (canonical):** `/opt/alpstein-ai/n8n/.env`  
**Example (committed):** `/opt/alpstein-ai/n8n/.env.example`

Compose should use:

```yaml
env_file:
  - .env
```

Working directory for compose commands: `/opt/alpstein-ai/n8n`.

### Required variables (names only)

| Variable | Purpose |
|----------|---------|
| `N8N_ENCRYPTION_KEY` | Encrypts credentials at rest in n8n volume — **generate once**, never change casually |
| `N8N_BASIC_AUTH_ACTIVE` | `true` for admin UI protection |
| `N8N_BASIC_AUTH_USER` | Admin username |
| `N8N_BASIC_AUTH_PASSWORD` | Admin password |
| `BACKEND_BASE_URL` | Base URL for HTTP Request node (no trailing slash) |
| `N8N_BACKEND_API_TOKEN` | Sent as `X-Alpstein-Webhook-Token` to backend |
| `GENERIC_TIMEZONE` | e.g. `Europe/Zurich` |
| `TZ` | Same as above |

Optional:

| Variable | Purpose |
|----------|---------|
| `ALPSTEIN_TEST_BUSINESS_ID` | Default `business_id` in normalize Code node |
| `N8N_HOST` | Public hostname when behind reverse proxy (production) |
| `WEBHOOK_URL` | Full webhook base URL if n8n must advertise correct URLs behind proxy |

**Never commit** `/opt/alpstein-ai/n8n/.env`. Add to `.gitignore` in implementation task.

---

## 7. `N8N_ENCRYPTION_KEY`

n8n requires this key to encrypt stored credentials (Telegram token, header auth, etc.).

| Rule | Detail |
|------|--------|
| Generate | `openssl rand -hex 32` (or n8n docs equivalent) |
| Store | Only in `n8n/.env` and secure backup |
| Stability | **Must stay constant** across container recreates using the same volume |
| Rotation | Changing key invalidates existing encrypted credentials — re-enter credentials in n8n UI |
| Repo | Never in git, workflow JSON, or docs |

If `N8N_ENCRYPTION_KEY` is missing on first start, n8n may generate one ephemerally — **avoid**; set explicitly before first run.

---

## 8. Admin / basic auth

Per `n8n-architecture.md` §10 and `deployment.md` §13:

- Enable **basic auth** on n8n UI via env vars (`N8N_BASIC_AUTH_*`).
- Bind host port to **127.0.0.1** only during dev.
- Production: HTTPS via nginx on `n8n.alpstein-ai.ch`, restrict source IPs or VPN where possible.
- Webhook endpoints inherit n8n’s public URL config; test webhooks use `/webhook-test/...` in editor mode.

n8n admin credentials are **separate** from `N8N_BACKEND_API_TOKEN` (backend webhook auth).

---

## 9. `BACKEND_BASE_URL` from n8n container

The workflow POST node calls:

```text
{{ $env.BACKEND_BASE_URL }}/api/v1/webhook/message
```

Choose URL by how backend runs:

### A. Current dev (backend on host — `0.0.0.0:8010`)

From inside `alpstein_n8n` on network **`alpstein-n8n_default`** (`172.20.0.0/16`, gateway **`172.20.0.1`**):

```text
BACKEND_BASE_URL=http://172.20.0.1:8010
```

**Do not** use `127.0.0.1` or `172.17.0.1` from this container — wrong network.

**UFW (required on this server):**

```bash
sudo ufw allow from 172.20.0.0/16 to any port 8010 proto tcp comment 'alpstein-n8n to host backend 8010'
```

Allows only the Alpstein compose subnet to reach host backend — **not** public internet.

Compose still provides `extra_hosts: host.docker.internal:host-gateway` for optional use on other hosts.

### B. Future — backend container on shared compose network

```text
BACKEND_BASE_URL=http://backend:8000
```

(or service name `alpstein_backend` — match compose service name exactly)

### C. Production — via nginx / public domain

```text
BACKEND_BASE_URL=https://alpstein-ai.ch
```

Use when n8n and backend communicate over public HTTPS (same as production checklist in env doc).

**Rule:** no trailing slash on `BACKEND_BASE_URL`.

**Token alignment:** `N8N_BACKEND_API_TOKEN` in `n8n/.env` must match backend `.env` (see env checklist §1).

---

## 10. Workflows folder usage

| Location | Role |
|----------|------|
| `n8n/workflows/*.json` | Git-tracked exports; code review (T13.8 strip secrets) |
| n8n volume `/home/node/.n8n` | Runtime source of truth after import |

**Workflow:**

1. Engineer updates JSON in repo (T13.x tasks).
2. Operator imports into n8n (`Import from File`).
3. Set env vars in n8n (from container env — already injected via `.env`).
4. Test via `/webhook-test/...`.
5. Activate workflow for production webhooks when Gate 3 passes.
6. Optional: export back to repo for drift control (T13.8).

No automatic sync in MVP — manual import is intentional and reviewable.

---

## 11. Avoiding conflict with `integrationhubspot_n8n`

| Risk | Mitigation |
|------|------------|
| Port collision | Alpstein uses **15679**, HubSpot uses **15678** |
| Container name collision | `alpstein_n8n` vs `integrationhubspot_n8n` |
| Volume collision | Separate named volume `alpstein_n8n_data` |
| Compose project collision | `docker-compose -p alpstein-n8n -f n8n/docker-compose.yml` |
| Accidental stop/remove | Never run compose down/stop against HubSpot project; document in runbook |
| Shared `.env` | HubSpot n8n has its own env — Alpstein uses **`/opt/alpstein-ai/n8n/.env` only** |
| Network | Default bridge is fine for host-gateway backend access; optional isolated network `alpstein_n8n_net` if needed later |

**Explicit rule:** T13.0 implementation must **not** `docker stop`, `docker rm`, `docker-compose down`, or edit compose files belonging to `integrationhubspot_n8n`.

Verify before first start:

```bash
docker ps --filter name=integrationhubspot_n8n
ss -tlnp | grep -E '15678|15679'
```

---

## 12. Implementation task (T13.0-impl)

**Status:** **implementation committed** — `n8n/docker-compose.yml`, `.env.example`, runtime runbook in repo.  
**Runtime:** **running** on `127.0.0.1:15679`; **HTTPS** via [`n8n-https-reverse-proxy.md`](../ops/n8n-https-reverse-proxy.md) (`https://n8n.alpstein-ai.ch`).

Task record: [`tasks/done/T13.0-implement-n8n-docker-compose.md`](../../tasks/done/T13.0-implement-n8n-docker-compose.md)

Delivered:

- `n8n/docker-compose.yml` ✓
- `n8n/.env.example` ✓
- `.gitignore` entry for `n8n/.env` ✓
- Runtime runbook: [`docs/ops/n8n-runtime-start.md`](n8n-runtime-start.md) ✓

**Out of scope for T13.0-impl:** nginx, full production stack, WhatsApp, workflow JSON changes.

---

## 13. Manual verification checklist (after T13.0-impl)

### Isolation

- [ ] `docker ps` shows `alpstein_n8n` **Up** and `integrationhubspot_n8n` still **Up** unchanged.
- [ ] `ss -tlnp | grep 15679` shows docker-proxy on **127.0.0.1** only.
- [ ] `15678` still belongs to HubSpot n8n.

### n8n health

- [ ] `http://127.0.0.1:15679` prompts basic auth.
- [ ] Login succeeds with `N8N_BASIC_AUTH_*` credentials.
- [ ] Volume `alpstein_n8n_data` exists and repopulates after container restart.

### Environment

- [ ] `N8N_ENCRYPTION_KEY` set before first launch (not empty).
- [ ] Inside container, `$BACKEND_BASE_URL` and `$N8N_BACKEND_API_TOKEN` are visible to workflows (n8n env injection).
- [ ] `BACKEND_BASE_URL` has no trailing slash.

### Backend connectivity (from n8n)

- [ ] Import `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`.
- [ ] Test webhook POST returns backend `success: true` (Gate 1).
- [ ] Wrong token → safe `N8N_BACKEND_REQUEST_FAILED` (502) from workflow error branch.

### Security hygiene

- [ ] `n8n/.env` not committed.
- [ ] No tokens in workflow export after import test.
- [ ] HubSpot n8n data/volumes untouched.

---

## 14. Relationship to T13 workflow slice

| Task | Dependency |
|------|------------|
| T13.0 plan | **This document** — done after review |
| T13.0-impl | Compose committed; **runtime** requires operator `docker-compose up` | Required for **Gate 1 runtime** on server |
| T13.4+ | Can proceed in parallel on any n8n instance; server Gate 1 needs **running `alpstein_n8n`** |

Recommended order: **T13.0 runtime start → Gate 1 verification → T13.4**.

**Gate 1:** Requires running **`alpstein_n8n`** runtime first (see [`n8n-runtime-start.md`](n8n-runtime-start.md)), then workflow import and test POST per [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md).

---

## 15. Production path (future — not T13.0)

Per deployment spec:

- Merge n8n into root compose with nginx, backend, postgres.
- Subdomain `n8n.alpstein-ai.ch` with TLS.
- `BACKEND_BASE_URL=https://alpstein-ai.ch` or internal `http://backend:8000` on Docker network.
- Migrate volume `alpstein_n8n_data` or export/import workflows.

Do not block MVP dev on full-stack compose.
