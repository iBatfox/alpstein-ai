# Alpstein Migration Engineer — Reference

Read only sections relevant to the current task.

## Specs (shape of DDL)

| Document | Use when |
|----------|----------|
| [database-schema.md](../../../specs/database/database-schema.md) | Columns, types, constraints, enums |
| [entities.md](../../../specs/database/entities.md) | Table purpose, relationships |
| [database-architecture.md](../../../specs/database/database-architecture.md) | Tenant isolation, who may write |
| [backend-architecture.md](../../../specs/architecture/backend-architecture.md) | `backend/alembic/`, models layout |

## Alembic layout (target)

```text
backend/
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── YYYYMMDD_HHMM_short_description.py
└── app/
    ├── db/
    └── models/
```

Confirm `env.py` and `alembic.ini` in the repo before running commands — URLs and metadata import paths may differ from templates below.

## Common commands

Run from `backend/` with env loaded (`.env` or exported `DATABASE_URL`):

```bash
# Inspect chain
alembic current
alembic heads
alembic history --verbose

# Create revision (prefer manual edit after autogen draft)
alembic revision -m "add_messages_table"
alembic revision --autogenerate -m "add_messages_table"

# Apply / roll back
alembic upgrade head
alembic upgrade +1
alembic downgrade -1
alembic downgrade <revision_id>
```

Do not print or commit `DATABASE_URL` values.

## Revision skeleton (explicit DDL)

```python
"""add example_table

Revision ID: 20260522_1200_add_example
Revises: <previous_revision>
Create Date: 2026-05-22 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260522_1200_add_example"
down_revision = "<previous_revision>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "example_table",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_example_table_tenant_id", "example_table", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_example_table_tenant_id", table_name="example_table")
    op.drop_table("example_table")
```

## Multi-step patterns

### Add NOT NULL column to populated table

1. Revision A: add column nullable (no default that lies about data).
2. Revision B: backfill in `upgrade()` (`op.execute` with parameterized SQL or ORM batch).
3. Revision C: `alter_column(..., nullable=False)` + FK/index if needed.

### Add index on large table

Prefer `op.create_index(..., postgresql_concurrently=True)` only if project `env.py` uses migration transactions that allow it; otherwise document maintenance window.

### Enum / status values

Match exact strings from `database-schema.md` (`active`, `new`, `whatsapp`, etc.). Changing allowed values = new migration + code alignment, not silent string drift.

## Chain hygiene

| Problem | Action |
|---------|--------|
| Multiple heads | `alembic heads` — merge revision or rebase branch with team; never apply unknown head on prod |
| Missing `down_revision` | Fix before merge; broken chain blocks deploy |
| Drift (DB ≠ models) | Compare `alembic current` vs expected head; inspect manual DB edits |
| Failed mid-upgrade | Restore from backup; fix revision; do not patch prod schema by hand without recording in Alembic |

## MVP tables (migration scope)

Core and AI config tables listed in [alpstein-database-architect/reference.md](../alpstein-database-architect/reference.md). Do not add `events`, `audit_logs`, soft delete, or dedicated/external DB routing without spec + MVP update.

## Coordination checklist

Before opening a PR:

- [ ] Database architect sign-off on shape (or spec already updated)
- [ ] Model files match migration
- [ ] Backend services updated if new columns are read/written (handoff to backend engineer)
- [ ] No n8n/AI direct DB assumptions introduced
