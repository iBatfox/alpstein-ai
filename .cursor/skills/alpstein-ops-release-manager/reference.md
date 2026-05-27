# Alpstein Ops Release Manager — Reference

Read only sections relevant to the release slice.

## Ops runbook index

| Topic | Path |
|-------|------|
| n8n deployment design | `docs/ops/n8n-deployment-plan.md` |
| n8n start / UFW / backend URL | `docs/ops/n8n-runtime-start.md` |
| Env + credentials (names only) | `docs/ops/n8n-env-credential-checklist.md` |
| Test webhook + Gate 1/2 | `docs/ops/n8n-workflow1-test-webhook.md` |
| Post–Gate 2 stabilization | `docs/ops/post-t13-5-stabilization.md` |
| HTTPS reverse proxy | `docs/ops/n8n-https-reverse-proxy.md` |
| Telegram mapping | `docs/ops/telegram-customer-ingress.md` |
| Telegram workflow ops | `docs/ops/n8n-workflow-telegram-customer-ingress.md` |
| DB recovery / Alembic | `docs/ops/database-recovery.md` |
| Contact block (ops) | `docs/architecture/pre-sales-contact-ownership.md` |
| Deployment architecture | `specs/architecture/deployment.md` |
| n8n architecture | `specs/architecture/n8n-architecture.md` |

## Server constants (this environment)

| Item | Value |
|------|--------|
| Repo root | `/opt/alpstein-ai` |
| Alpstein n8n compose | `/opt/alpstein-ai/n8n/docker-compose.yml` |
| Alpstein n8n env | `/opt/alpstein-ai/n8n/.env` (gitignored) |
| Container | `alpstein_n8n` |
| Compose project | `alpstein-n8n` |
| Host bind | `127.0.0.1:15679` → container `5678` |
| n8n HTTPS | `https://n8n.alpstein-ai.ch` |
| HubSpot n8n (do not touch) | `integrationhubspot_n8n` @ `127.0.0.1:15678` |
| Postgres container | `backend_postgres` @ `127.0.0.1:15432` |
| Backend from container | `http://172.20.0.1:8010` |
| Docker bridge (Alpstein n8n) | `172.20.0.0/16` (`alpstein-n8n_default`) |
| CLI | `docker-compose` (v1.29) |

## Verification commands

```bash
# HubSpot isolation check
docker ps --filter name=integrationhubspot_n8n
ss -tlnp | grep -E '15678|15679'

# Alpstein n8n health
docker ps --filter name=alpstein_n8n
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:15679/

# Backend health (host)
curl -sS http://127.0.0.1:8010/api/v1/health

# Backend health (from n8n container)
docker exec alpstein_n8n wget -qO- http://172.20.0.1:8010/api/v1/health

# Backend tests
cd /opt/alpstein-ai/backend && pytest -q

# Alembic current
cd /opt/alpstein-ai/backend && alembic current
```

## Webhook auth (release debugging)

| Check | Expected |
|-------|----------|
| Header | `X-Alpstein-Webhook-Token` |
| Backend env | `N8N_BACKEND_API_TOKEN` |
| n8n env | `N8N_BACKEND_API_TOKEN` (same value) |
| Wrong/missing token | `401` / `403` per backend behavior |

## Workflow export hygiene

Before any commit of `n8n/workflows/*.json`:

- Remove secret values from credential objects.
- Prefer stripping credential **IDs** in scrubbed exports (re-bind on import).
- Keep topology and node names aligned with ops doc.
- Filename patterns: `t13_*`, `alpstein-incoming-message-test_gate2_YYYY-MM-DD.json` (backups).

Canonical repo export for test path: `n8n/workflows/t13_workflow1_test_webhook_skeleton.json` (name may evolve — match ops doc).

## Project-status sync (after accepted release)

Hand off to **alpstein-project-archivist**:

| File | Action |
|------|--------|
| `docs/project-status/completed.md` | Append factual entry with ops doc link |
| `docs/project-status/next-steps.md` | Close completed gate; single queue |
| `docs/project-status/current-state.md` | Regenerate if runtime truth changed |
| `tasks/*` | Move to `done/` only after human acceptance |

## Known release risks (audit backlog)

Use [`docs/project-status/historical/engineering-audit-report.md`](../../../docs/project-status/historical/engineering-audit-report.md) for drift backlog — common items:

- Workflow export `active: false` while ops claims production
- T14.5 / T14.6 not signed off
- Polluted `messages` history causing greeting loops (DB content — not fixed by deploy alone)
- Orphan workflow `n8n/workflows/My_workflow.json` not in ops docs

Do not mark these resolved in status docs without evidence.

## Out of scope

- Implementing n8n nodes or backend features (other skills)
- Editing `specs/` without explicit spec task
- HubSpot n8n or `/hubspot_clone` paths
- Inventing new ports, domains, or compose layouts
- Unattended production `docker-compose down` on shared server
