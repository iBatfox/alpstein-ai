# Phase F.1 — ERPNext Installation & Operational Architecture

**Doc status:** architecture / design (no integration)  
**As-of:** 2026-05-29  
**Branch:** `stabilization/runtime-baseline`  
**Server:** Contabo VPS `144.91.113.184`  
**Public URL:** `https://crm.alpstein-ai.ch`  
**DNS:** `A` record `crm.alpstein-ai.ch` → `144.91.113.184`

**Prerequisites:** E2/E3 complete on Alpstein stack ([`runtime-map.md`](../ops/runtime-map.md))

**Out of scope (F.1):** Alpstein ↔ ERPNext sync, adapters, CRM API integration, PostgreSQL ownership changes, observability wiring, billing.

**Phase F.2 starts only after:** ERPNext deployed, HTTPS verified, backup/restore drill documented, human review accepted.

---

## 0. Architectural boundary (non-negotiable)

```text
Channels → n8n → Alpstein Backend → PostgreSQL (SOURCE OF TRUTH)
                                      │
                                      │  (future read-only / API sync — NOT F.1)
                                      ▼
                                   ERPNext (MariaDB)
                                      │
                                      └── Operations UI / CRM / dashboards (human)
```

| System | Role in platform | Database |
|--------|------------------|----------|
| **Alpstein PostgreSQL** | Runtime SoT: messages, leads, tenants, AI config, observability | PostgreSQL (`alpstein_postgres`) |
| **ERPNext** | Operations center, CRM UI, future business monitoring | **MariaDB** (isolated) |

ERPNext must **not**:

- Own orchestration or replace n8n/backend
- Become runtime database for Alpstein
- Host integration workers for Telegram/WhatsApp ingress
- Expose MariaDB/Redis ports to the public internet

---

## 1. Recommended architecture

### 1.1 Preferred model

**Isolated Docker Compose stack** for ERPNext (official `frappe_docker` pattern), **sibling** to the Alpstein `alpstein-ai` compose project, with **host nginx** for TLS termination — same operational pattern as `n8n.alpstein-ai.ch`.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Host: 144.91.113.184 (Ubuntu)                                                │
│                                                                              │
│  PUBLIC (UFW)                                                                │
│    :80   → nginx → 301 → HTTPS                                               │
│    :443  → nginx → vhosts                                                    │
│                                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐         │
│  │ Compose: alpstein-ai        │  │ Compose: alpstein-erpnext    │         │
│  │ Network: alpstein_internal  │  │ Network: erpnext_internal    │         │
│  │  • alpstein_postgres :5432  │  │  • mariadb :3306 (private)   │         │
│  │  • alpstein_backend :8000   │  │  • redis :6379 (private)       │         │
│  │  • alpstein_n8n_compose     │  │  • erpnext-web :8080         │         │
│  │    :15679 loopback          │  │  • workers / scheduler       │         │
│  └──────────────┬──────────────┘  └──────────────┬──────────────┘         │
│                 │ NO bridge in F.1                 │                         │
│                 └──────────────────────────────────┘                         │
│                                                                              │
│  nginx (host)                                                                │
│    crm.alpstein-ai.ch:443  → 127.0.0.1:18080  (erpnext frontend)            │
│    n8n.alpstein-ai.ch:443  → 127.0.0.1:15679  (existing)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why this model

| Criterion | Assessment |
|-----------|------------|
| **Operational complexity** | Medium — one extra compose project + nginx vhost; matches existing team skills |
| **Maintainability** | High — version-pinned images, volumes per role, separate backups |
| **Upgrade path** | Documented frappe/ERPNext image bumps + `bench migrate` in container |
| **Isolation from Alpstein** | Strong — separate networks, DB engines, compose project names |
| **TLS** | Reuse proven host nginx + certbot pattern |

### 1.3 Pros and cons

| Approach | Pros | Cons |
|----------|------|------|
| **Docker Compose (recommended)** | Isolation; official `frappe_docker`; pin versions; portable backups; no host Python bench pollution | ~1–2 GB extra RAM; multi-container stack; frappe upgrade discipline required |
| **Bench on host** | Familiar to Frappe community; direct `bench` CLI | Conflicts with Alpstein Docker; harder rollback; host dependency drift; not aligned with current SoT |
| **Traefik-only edge** | Automatic TLS per container | Second edge stack beside nginx; operator already standardized on nginx |
| **Single mega-compose with Alpstein** | One `docker compose` command | **Rejected** — blast radius, resource coupling, violates separation |

---

## 2. Deployment decision

### **Chosen: Option A — ERPNext Docker**

**Not chosen: Option B — ERPNext Bench** (bare-metal / host install)

### Justification

1. **Consistency** — Alpstein production already uses `docker compose` v2, loopback binds, and host nginx ([`runtime-map.md`](../ops/runtime-map.md)).
2. **Isolation** — ERPNext requires MariaDB + Redis + workers; keeping them in `erpnext_internal` avoids touching `alpstein_postgres` and backend networking.
3. **Official path** — Frappe maintains [`frappe_docker`](https://github.com/frappe/frappe_docker) for production-style deployments with pinned `frappe/erpnext` images.
4. **Rollback** — Image tag + volume snapshot restore is faster than host bench rebuilds on a shared VPS.
5. **Security** — No public container ports; only `127.0.0.1:18080` (or similar) published to host nginx.

Bench remains valid for **development** or a **dedicated ERP-only server**; it is a poor fit for **co-located** production with Alpstein on one VPS.

---

## 3. Server sizing

Assumes ERPNext is **internal ops/CRM** (staff users), not 200 end-customer tenants on Frappe in F.1. Future multi-tenant ERP dashboards may require rescaling.

Also assume **shared host** with Alpstein (postgres + backend + n8n). Sizes below are **incremental for ERPNext stack**; total VPS must include Alpstein baseline (~4–8 GB RAM in use today).

### Small deployment (1–10 staff / single company site)

| Resource | ERPNext stack | Suggested **total VPS** (Alpstein + ERP) |
|----------|---------------|------------------------------------------|
| **CPU** | 2 vCPU dedicated headroom | 4–6 vCPU |
| **RAM** | 4 GB (MariaDB 1.5G + ERPNext 1.5G + Redis/workers 1G) | 12–16 GB |
| **Disk** | 40 GB (DB 20G + sites 10G + logs/backups 10G) | 80–120 GB SSD |

### Medium deployment (10–50 staff / light multi-company)

| Resource | ERPNext stack | Suggested **total VPS** |
|----------|---------------|-------------------------|
| **CPU** | 4 vCPU | 8 vCPU |
| **RAM** | 8 GB | 24–32 GB |
| **Disk** | 100 GB | 200–300 GB SSD |

### Growth deployment (50–200 staff / heavy documents & integrations later)

| Resource | ERPNext stack | Suggested **total VPS** |
|----------|---------------|-------------------------|
| **CPU** | 8 vCPU | 16+ vCPU |
| **RAM** | 16 GB | 48–64 GB |
| **Disk** | 250 GB+ | 500 GB+ SSD (or split DB to managed MariaDB) |

**Contabo check:** Before install, capture `free -h`, `df -h`, `docker stats` on production host. If RAM &lt; 12 GB free under load, upgrade VPS before ERPNext.

---

## 4. Database analysis

### 4.1 ERPNext runtime components

| Component | Purpose | F.1 deployment |
|-----------|---------|----------------|
| **MariaDB 10.6+** | Primary ERP metadata & transactions | Dedicated container + volume |
| **Redis** | Cache, socketio, background jobs | Dedicated container |
| **Gunicorn / Werkzeug** | Web app (`erpnext-web`) | Container |
| **Workers** | RQ/default workers for async jobs | Container(s) |
| **Scheduler** | `bench schedule` cron equivalent | Container |
| **Nginx (optional)** | In-stack frontend proxy | Prefer **host nginx** for TLS; in-stack nginx binds loopback only |

### 4.2 Why ERPNext cannot use Alpstein PostgreSQL

| Reason | Explanation |
|--------|-------------|
| **Framework contract** | Frappe ORM and ERPNext schema target **MariaDB/MySQL** (InnoDB), not PostgreSQL |
| **Migrations** | `bench migrate` generates MariaDB-specific DDL; running on PG is unsupported |
| **Operational ownership** | Mixing engines would blur SoT; Alpstein PG remains automation SoT; ERP is operational mirror/UI |
| **Performance profile** | ERPNext expects MariaDB tuning (buffer pool, etc.) |

### 4.3 Separation of concerns

```text
┌──────────────────────┐         ┌──────────────────────┐
│ alpstein_postgres    │         │ erpnext_mariadb      │
│ (PostgreSQL)         │   F.2+  │ (MariaDB)            │
│                      │ ──────► │ read via API/ETL only │
│ tenants, messages,   │  future │ CRM entities,        │
│ leads, traces        │  sync   │ invoices, HR, etc.   │
└──────────────────────┘         └──────────────────────┘
        ▲                                    ▲
        │ SoT                                  │ Ops UI only (F.1)
   Alpstein Backend                      ERPNext App
```

**F.1:** No network link between databases. No shared volumes. No cross-compose `depends_on`.

---

## 5. Backup strategy

### 5.1 What to back up

| Layer | Method | Frequency |
|-------|--------|-----------|
| **MariaDB** | `mariadb-dump` / `bench backup` from worker container | Daily |
| **Sites volume** | `sites/` tar (assets, private files, site config) | Daily |
| **Compose env** | Copy `/opt/alpstein-erpnext/.env` (no secrets in git) | On change |
| **Application** | Pin image digests in `.env` + git tag of compose overrides | Per release |

### 5.2 Retention policy (recommended)

| Tier | Retention | Storage |
|------|-----------|---------|
| **Daily** | 7 days | `/var/backups/erpnext/daily/` |
| **Weekly** | 4 weeks | `/var/backups/erpnext/weekly/` |
| **Monthly** | 6 months | Off-host copy (S3-compatible / another VPS) |

Encrypt off-host backups at rest (provider-side or `gpg` before upload). **Never** commit dumps to git.

### 5.3 Disaster recovery procedure (outline)

1. Stop ERPNext workers (prevent writes): `docker compose -p alpstein-erpnext stop backend worker scheduler`  
2. Restore MariaDB dump to fresh volume or new container  
3. Restore `sites` volume from tar  
4. Start stack with **same pinned image tags** as backup manifest  
5. Verify `https://crm.alpstein-ai.ch` login, desk load, scheduler heartbeat  
6. Record RTO/RPO in ops evidence log  

**RPO target:** 24h (daily dump) unless hourly dumps added later.  
**RTO target:** 2–4h operator-led (documented).

---

## 6. Update strategy

### 6.1 Principles

- **Pin versions** in `.env` (`ERPNEXT_VERSION`, `FRAPPE_VERSION` — exact tags from frappe_docker release notes).  
- **Never** `latest` in production.  
- **Backup before upgrade** (DB + sites).  
- **Staging** recommended before production bump (see §8.4).

### 6.2 Safe upgrade flow (production)

```text
1. Announce maintenance window (ERP UI only — Alpstein ingress unaffected)
2. Full backup (MariaDB + sites) → verify dump size
3. On staging OR production:
   a. Pull new pinned images only
   b. docker compose up -d (recreate app containers)
   c. docker compose exec backend bench --site <site> migrate
   d. docker compose exec backend bench --site <site> clear-cache
4. Smoke: login, open Sales / User list, check scheduler logs
5. If fail → restore volumes from backup; re-pin previous image tags
```

### 6.3 Rollback

| Step | Action |
|------|--------|
| 1 | Stop compose project |
| 2 | Restore MariaDB + sites volumes from pre-upgrade backup |
| 3 | Set `.env` image tags to previous known-good |
| 4 | `docker compose up -d` |
| 5 | Verify HTTPS + desk |

### 6.4 Staging recommendation

| Option | Pattern |
|--------|---------|
| **Preferred** | Second subdomain `staging.crm.alpstein-ai.ch` on same host, loopback port `18081`, separate compose project or `sites` prefix |
| **Minimal** | Restore backup clone on non-production VPS |

Staging must **not** point at `alpstein_postgres`.

---

## 7. Production hardening

| Area | Recommendation | Priority |
|------|----------------|----------|
| **HTTPS** | Host nginx + Let's Encrypt for `crm.alpstein-ai.ch` only | P0 |
| **Firewall (UFW)** | Allow `22` (restricted IP), `80`, `443`; deny all other inbound | P0 |
| **No public ERP ports** | Do not publish `8000/8080/3306/6379` on `0.0.0.0` | P0 |
| **Docker networks** | `erpnext_internal` not linked to `alpstein_internal` in F.1 | P0 |
| **Secrets** | `/etc/alpstein/erpnext.env` mode `600`; DB root password random 32+ | P0 |
| **ERPNext admin** | Strong passwords; 2FA if available; limit `Administrator` sharing | P0 |
| **nginx** | `client_max_body_size` for uploads; timeouts ≥ 300s for reports | P1 |
| **MariaDB** | Non-root app user; no public bind | P0 |
| **Redis** | `requirepass` if exposed beyond loopback (frappe_docker default internal) | P1 |
| **Monitoring** | Uptime check `https://crm.alpstein-ai.ch/api/method/ping` or login page; disk/RAM alerts | P1 |
| **Logging** | `docker compose logs` → journald; logrotate for nginx | P2 |
| **Health checks** | Compose `healthcheck` on MariaDB + web; nginx `proxy_next_upstream` optional | P2 |
| **Updates** | OS unattended security only; ERPNext manual pinned upgrades | P1 |
| **HubSpot n8n** | Do not modify `15678` / `integrationhubspot_n8n` | P0 |

### 7.1 Firewall rules (reference)

```bash
# Example — operator adjusts SSH source IPs
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <ADMIN_IP> to any port 22 proto tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 8. Network diagram (ports)

```text
                         INTERNET
                             │
                    DNS A record
              crm.alpstein-ai.ch → 144.91.113.184
                             │
              ┌──────────────┴──────────────┐
              │  PUBLIC HOST FIREWALL      │
              │  :80  (HTTP → 301 HTTPS)   │  ◄── PUBLIC
              │  :443 (HTTPS)              │  ◄── PUBLIC
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │  nginx (host)   │
                    │  TLS terminate  │
                    │  Let's Encrypt  │
                    └────────┬────────┘
                             │ proxy_pass
                             │ 127.0.0.1:18080  ◄── LOOPBACK ONLY
                             │
         ┌───────────────────▼───────────────────┐
         │  Docker network: erpnext_internal      │
         │                                        │
         │  ┌─────────────┐    ┌──────────────┐  │
         │  │ erpnext-web │    │  mariadb     │  │
         │  │ :8080 int   │───►│  :3306 int   │  │
         │  └──────┬──────┘    └──────────────┘  │
         │         │           PRIVATE           │
         │  ┌──────▼──────┐    ┌──────────────┐  │
         │  │ redis       │    │ workers +    │  │
         │  │ :6379 int   │    │ scheduler    │  │
         │  └─────────────┘    └──────────────┘  │
         └────────────────────────────────────────┘

Alpstein stack (unchanged, no bridge in F.1):

         ┌────────────────────────────────────────┐
         │  Docker network: alpstein_internal     │
         │  postgres:5432, backend:8000, n8n      │
         │  127.0.0.1:15679 / :8000 / :15433       │
         └────────────────────────────────────────┘
```

| Port | Exposure | Service |
|------|----------|---------|
| **443** | Public | nginx → ERPNext |
| **80** | Public | nginx ACME + redirect |
| **18080** | Loopback | ERPNext frontend (host publish) |
| **8080** | Docker internal | ERPNext web container |
| **3306** | Docker internal | MariaDB |
| **6379** | Docker internal | Redis |
| **22** | Admin IP only | SSH |

**Forbidden public access:** `http://144.91.113.184:8000`, `:8080`, `:18080`, `:3306`.

---

## 9. Step-by-step deployment plan (operator execution)

> **Human operator executes** on the server. Agent does not run these without explicit approval.  
> Commands assume Ubuntu 22.04/24.04, root or sudo, Docker already installed for Alpstein.

Detailed copy-paste runbook: [`docs/ops/erpnext-production-deployment-runbook.md`](../ops/erpnext-production-deployment-runbook.md).

### Phase checklist

| Step | Summary |
|------|---------|
| F.1.1 | Preflight: RAM/disk, DNS, firewall |
| F.1.2 | Install directory `/opt/alpstein-erpnext`, clone `frappe_docker` |
| F.1.3 | Configure `.env` (pinned versions, site name, DB passwords) |
| F.1.4 | `docker compose` up MariaDB/Redis, create site, start ERPNext |
| F.1.5 | Bind ERPNext to `127.0.0.1:18080` |
| F.1.6 | nginx vhost + certbot `crm.alpstein-ai.ch` |
| F.1.7 | Verification + first backup |
| F.1.8 | Document evidence in runbook § Evidence |

---

## 10. Reviewer findings (alpstein-reviewer)

### Review summary

**Pass with notes** for F.1 architecture — proceed to operator deployment using isolated Docker + host nginx. **Block F.2 integration** until ERPNext is live, backed up, and HTTPS verified.

### Architectural risks

| ID | Risk | Level | Mitigation |
|----|------|-------|------------|
| R1 | ERPNext on same VPS exhausts RAM with Alpstein+n8n | **HIGH** | Measure baseline; upgrade VPS; set MariaDB `innodb_buffer_pool_size` cap |
| R2 | Accidental docker network link exposes MariaDB | **MEDIUM** | Separate compose project; no `external_links`; review `docker network ls` |
| R3 | Operator uses IP:8080 bypassing TLS | **MEDIUM** | UFW deny non-80/443; nginx-only vhost; ops training |
| R4 | Confusion: ERPNext DB vs Alpstein SoT | **MEDIUM** | Document boundary in F.1/F.2; no sync in F.1 |
| R5 | frappe upgrade breaks customizations | **LOW** (F.1) | No custom apps in F.1; pin versions |

### Operational risks

| ID | Risk | Level | Mitigation |
|----|------|-------|------------|
| O1 | Backup not tested until incident | **HIGH** | Quarterly restore drill to staging |
| O2 | certbot failure expires TLS | **MEDIUM** | Monitoring + `certbot renew --dry-run` monthly |
| O3 | Disk fill from sites/uploads | **MEDIUM** | Quotas, alerts at 80% disk |
| O4 | Single-server SPOF | **MEDIUM** | Accept for MVP; document RTO; off-host backups |

### Maintenance risks

| ID | Risk | Level | Mitigation |
|----|------|-------|------------|
| M1 | frappe_docker upstream compose changes | **MEDIUM** | Pin git tag of frappe_docker; minimal overrides in repo |
| M2 | ERPNext v15 vs v16 migration | **LOW** (F.1) | Pick one major line; stay on LTS release notes |
| M3 | Two edge patterns (nginx + future Traefik) | **LOW** | Standardize on host nginx only |

### Scaling risks (future)

| ID | Risk | Level | Mitigation |
|----|------|-------|------------|
| S1 | 50+ customers on one ERP instance | **HIGH** (future) | Multi-site bench or split instances — not F.1 |
| S2 | Sync load from Alpstein PG | **MEDIUM** (F.2+) | Queue-based ETL; read replicas — design in F.2 |

### Scope check

- **MVP alignment:** **yes** for F.1 install-only — ERPNext as ops layer is post-MVP but explicitly approved by Phase F charter.  
- **No forbidden integration** in this deliverable.

### Specs / docs consulted

- [`docs/ops/runtime-map.md`](../ops/runtime-map.md)  
- [`docs/ops/n8n-https-reverse-proxy.md`](../ops/n8n-https-reverse-proxy.md)  
- [`docs/architecture/canonical-runtime-architecture.md`](canonical-runtime-architecture.md)  
- Frappe `frappe_docker` production documentation (external)

### What was not reviewed

- Live `free -h` / `docker stats` on `144.91.113.184` (operator must capture pre-install)  
- Legal/licensing ERPNext (open source GPLv3 — operator compliance)  
- F.2 sync API design

---

## 11. Success criteria (F.1)

- [ ] `https://crm.alpstein-ai.ch` serves ERPNext login over valid TLS  
- [ ] No ERP container ports on `0.0.0.0` except loopback publish to nginx  
- [ ] MariaDB/Redis not reachable from internet  
- [ ] Alpstein stack (`n8n`, `backend`, `alpstein_postgres`) unchanged and healthy  
- [ ] Daily backup script documented + one successful test restore  
- [ ] Pinned image versions recorded  
- [ ] Human review → move task to `tasks/done/` → begin F.2 planning only after acceptance

---

## 12. Related files

| Document | Purpose |
|----------|---------|
| [`docs/ops/erpnext-production-deployment-runbook.md`](../ops/erpnext-production-deployment-runbook.md) | Operator commands |
| [`tasks/todo/T-f1-erpnext-installation-operational-architecture.md`](../../tasks/todo/T-f1-erpnext-installation-operational-architecture.md) | Task tracking |
