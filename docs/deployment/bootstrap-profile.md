# Bootstrap profile (B2.8)

**Contract:** [`deployment-contract.md`](deployment-contract.md) §5.4, §12  
**Compose:** [`docker-compose.yml`](../../docker-compose.yml) service `backend-bootstrap` (profile `bootstrap`)  
**Script:** [`backend/docker-bootstrap.sh`](../../backend/docker-bootstrap.sh)

Optional **dev/test-only** one-shot that seeds demo businesses after migrations. **Never** runs on normal `docker-compose up`.

---

## Bootstrap policy

| Rule | Behavior |
|------|----------|
| Who runs seed | Operator explicitly: `--profile bootstrap` |
| Normal `up` | Postgres + backend (+ n8n) only — **no seed** |
| Allowed environments | `development`, `dev`, `local`, `test` |
| Refused environments | `production`, `staging`, or any other value |
| Migrations | **Backend entrypoint only** — bootstrap does not re-run Alembic |
| n8n workflows | **Not** imported or activated |
| Production data | **No** fake production rows |

---

## Seed order (fresh volume)

```text
1. docker-compose up -d postgres backend     → alembic upgrade head (0001–0007)
2. docker-compose --profile bootstrap run --rm backend-bootstrap
     a. scripts/seed_dev_ai_configuration.py  → demo_barbershop_001 + AI config
     b. scripts/demo_business_separation.sql  → alpstein_ai_demo_001
     c. scripts/update_alpstein_pre_sales_behavior.sql → demo content tweaks
3. (optional) Gate 1 webhook smoke — requires N8N_BACKEND_API_TOKEN + business_id
```

---

## Compose service

| Attribute | Value |
|-----------|--------|
| Service | `backend-bootstrap` |
| Profile | `bootstrap` |
| Container | `alpstein_backend_bootstrap` |
| Image | Same as `backend` (`alpstein-ai-backend:local`) |
| Entrypoint | `/app/docker-bootstrap.sh` |
| Depends on | `backend` healthy (migrations + readiness done) |
| Restart | `no` (one-shot) |

---

## Environment variables

Set in repo root `.env` (see [`.env.example`](../../.env.example)):

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `POSTGRES_PASSWORD` | **Yes** | — | SQL `psql` + URL interpolation |
| `ALPSTEIN_AI_ENVIRONMENT` | **Yes** (dev) | `development` in compose | Seed guard |
| `ALPSTEIN_AI_DATABASE_URL` | Set by compose | — | Python seed |
| `RUN_SQL_BOOTSTRAP` | No | `true` | Set `false` to run Python seed only |

---

## Operator commands

From repo root:

```bash
# 1) Stack without bootstrap
docker-compose -p alpstein-ai up -d postgres backend

# 2) Explicit bootstrap (dev only)
docker-compose -p alpstein-ai --profile bootstrap run --rm backend-bootstrap

# 3) Verify demo business exists (dev overlay + psql)
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml exec postgres \
  psql -U alpstein -d alpstein_ai -c "SELECT external_id FROM businesses;"
```

Production-like refusal test:

```bash
docker-compose -p alpstein-ai --profile bootstrap run --rm \
  -e ALPSTEIN_AI_ENVIRONMENT=production \
  backend-bootstrap
# Expect exit 1 — bootstrap refused
```

---

## Rollback

| Action | Effect |
|--------|--------|
| `docker-compose -p alpstein-ai down` | Stop stack; bootstrap container already exited |
| `docker volume rm alpstein_postgres_data` | **Data loss** — empty DB; re-run migrations + bootstrap |
| Revert B2.8 compose commit | Remove profile service; image still contains scripts (harmless) |

RBU: volume snapshot before bootstrap on non-disposable DBs.

---

## Out of scope

- Automatic seed on `compose up`
- n8n workflow import/activation
- Contabo host runtime changes

---

## Related

- [`postgres-compose.md`](postgres-compose.md)
- [`backend-image.md`](backend-image.md)
- [`database-recovery.md`](../ops/database-recovery.md)
