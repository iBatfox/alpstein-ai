**Doc status:** runtime-derived  
**Tier:** ops/migration (pending move)

# Database recovery (Alpstein AI backend)

Short reference when PostgreSQL was recreated or is empty. **No secrets in this doc.**

---

## Alembic revisions

Current chain: **`0001` … `0007`**

| Revision | Scope (summary) |
|----------|-------------------|
| 0001 | tenants, businesses |
| 0002 | customers |
| 0003 | conversations |
| 0004 | messages |
| 0005 | message idempotency index |
| 0006 | AI configuration tables, `prompt_runs` |
| 0007 | `leads` |

**Renumbering** migration files is safe **only** on an **empty** database (or after full recreate). Never renumber on a DB that already applied old revision IDs.

---

## After DB recreate

From `backend/` with `ALPSTEIN_AI_DATABASE_URL` set in `.env`:

```bash
cd /opt/alpstein-ai/backend
alembic upgrade head
```

Then seed demo data for n8n Gate 1 / test webhook (`business_id` **`demo_barbershop_001`**):

```bash
export ALPSTEIN_AI_ENVIRONMENT=development
python scripts/seed_dev_ai_configuration.py
```

Ensure tenant/business rows exist for `demo_barbershop_001` (seed script covers AI config; add manual business seed if your environment uses a separate tenants/businesses bootstrap).

---

## n8n / Gate 1 dependency

Without migrations + seed, `POST /api/v1/webhook/message` may return `BUSINESS_NOT_FOUND` or empty AI config. See [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md).

---

## Related

- [`n8n-runtime-start.md`](n8n-runtime-start.md) — container → `http://172.20.0.1:8010`
- [`docs/project-status/current-state.md`](../project-status/current-state.md) — schema status
