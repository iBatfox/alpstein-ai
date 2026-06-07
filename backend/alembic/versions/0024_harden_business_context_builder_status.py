"""harden_business_context_builder_status

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "business_context_builder"
TABLE = "sessions"
CONSTRAINT = "business_context_builder_sessions_status_check"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, schema=SCHEMA, type_="check")
    op.execute(
        sa.text(
            """
            UPDATE business_context_builder.sessions
            SET status = CASE
                WHEN status IN ('created', 'in_progress') THEN 'active'
                WHEN status = 'archived' THEN 'cancelled'
                ELSE status
            END
            """
        )
    )
    op.alter_column(
        TABLE,
        "status",
        schema=SCHEMA,
        server_default="active",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )
    op.create_check_constraint(
        CONSTRAINT,
        TABLE,
        "status IN ('active', 'completed', 'cancelled')",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, schema=SCHEMA, type_="check")
    op.execute(
        sa.text(
            """
            UPDATE business_context_builder.sessions
            SET status = CASE
                WHEN status = 'active' THEN 'in_progress'
                WHEN status = 'cancelled' THEN 'archived'
                ELSE status
            END
            """
        )
    )
    op.alter_column(
        TABLE,
        "status",
        schema=SCHEMA,
        server_default="in_progress",
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )
    op.create_check_constraint(
        CONSTRAINT,
        TABLE,
        "status IN ('created', 'in_progress', 'completed', 'archived')",
        schema=SCHEMA,
    )
