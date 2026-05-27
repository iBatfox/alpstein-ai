# Fix Alembic revision IDs for VARCHAR(32) (done)

**Status:** Complete. Migration metadata only; no schema/model changes.

## Problem

`alembic_version.version_num` is `VARCHAR(32)`. Long revision IDs (e.g. `0001_create_tenants_and_businesses`, 35 chars) caused:

```text
value too long for type character varying(32)
```

## Change

| File (unchanged) | Old `revision` | New `revision` | `down_revision` |
|------------------|----------------|----------------|-----------------|
| `0001_create_tenants_and_businesses.py` | `0001_create_tenants_and_businesses` | `0001` | `None` |
| `0002_create_customers.py` | `0002_create_customers` | `0002` | `0001` |
| `0003_create_conversations.py` | `0003_create_conversations` | `0003` | `0002` |
| `0004_create_messages.py` | `0004_create_messages` | `0004` | `0003` |
| `0005_add_messages_business_external_message_id_unique.py` | `0005_add_messages_business_external_message_id_unique` | `0005` | `0004` |
| `0006_create_ai_configuration_and_prompt_runs.py` | `0006_create_ai_configuration_and_prompt_runs` | `0006` | `0005` |
| `0007_create_leads.py` | `0007_create_leads` | `0007` | `0006` |

Docstring `Revision ID` / `Revises` headers updated to match.

## Validation (dev)

```bash
cd backend
.venv/bin/alembic heads    # 0007 (head)
.venv/bin/alembic history   # linear 0001 -> ... -> 0007
.venv/bin/python -m pytest tests/test_alembic_migration.py -q  # 8 passed
```

With `.env` loaded, `alembic upgrade head` completed all revisions; `alembic current` → `0007`.

## Manual DB recovery (fresh / failed partial migrate)

If a database was left with partial tables from a failed long-ID stamp, **drop and recreate** before re-running migrations (do not apply to production without a planned migration strategy):

```bash
sudo -u postgres dropdb alpstein_ai
sudo -u postgres createdb alpstein_ai
cd /opt/alpstein-ai/backend
set -a; source /opt/alpstein-ai/.env; set +a
./.venv/bin/alembic upgrade head
./.venv/bin/alembic current   # expect: 0007 (head)
```

**Production note:** If `alembic_version` already stores a long revision string, stamp/downgrade strategy must be agreed with the operator before changing live DBs.
